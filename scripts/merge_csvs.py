"""
CSV Merge ETL — Consolidate all LinkedIn job CSV files into one clean file.

Reads 8 CSV files with 4 different schemas, normalizes columns to match
the Postgres `jobs` table, deduplicates by LinkedIn job ID, removes records
with missing critical data, and outputs a single clean CSV + detailed report.
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

CSV_DIR = r"D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\migrations\CSV"
OUTPUT_FILE = r"D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\migrations\jobs_merged_final.csv"

# Target columns matching the DB schema
TARGET_COLS = [
    "job_id", "job_title", "company_name", "job_description", "location",
    "salary_info", "seniority_level", "employment_type", "work_type",
    "contract_type", "sector", "job_url", "apply_url", "company_url",
    "time_posted", "num_applicants", "recruiter_name", "recruiter_url",
    "source_file"
]

# ─── Schema Mappings ────────────────────────────────────────────────

# Schema A: dataset_linkedin-job-scraper (23 cols, comma)
SCHEMA_A = {
    "job_id": "jobId",
    "job_title": "jobTitle",
    "company_name": "companyName",
    "job_description": "jobDescription",
    "location": "location",
    "salary_info": "salaryInfo/0",
    "seniority_level": "experienceLevel",
    "employment_type": "contractType",
    "work_type": "workType",
    "contract_type": "contractType",
    "sector": "sector",
    "job_url": "jobUrl",
    "apply_url": "applyUrl",
    "company_url": "companyUrl",
    "time_posted": "postedTime",
    "num_applicants": "applicationsCount",
    "recruiter_name": "posterFullName",
    "recruiter_url": "posterProfileUrl",
}

# Schema B: dataset_linkedin-job-search (237 cols, comma)
SCHEMA_B = {
    "job_id": "id",
    "job_title": "title",
    "company_name": "company/name",
    "job_description": "descriptionText",
    "location": "location/linkedinText",
    "salary_info": "salary/text",
    "seniority_level": "experienceLevel",
    "employment_type": "employmentType",
    "work_type": "workplaceType",
    "contract_type": None,
    "sector": "industries/0",
    "job_url": "linkedinUrl",
    "apply_url": "easyApplyUrl",
    "company_url": "company/url",
    "time_posted": "postedDate",
    "num_applicants": "applicantsCount",
    "recruiter_name": "hiringTeam/0/name",
    "recruiter_url": "hiringTeam/0/linkedinUrl",
}

# Schema C: dataset_linkedin-jobs-scraper_02-09 (37 cols, comma)
SCHEMA_C = {
    "job_id": "id",
    "job_title": "title",
    "company_name": "companyName",
    "job_description": "descriptionText",
    "location": "location",
    "salary_info": "salary",
    "seniority_level": "seniorityLevel",
    "employment_type": "employmentType",
    "work_type": None,
    "contract_type": None,
    "sector": "industries",
    "job_url": "link",
    "apply_url": "applyUrl",
    "company_url": "companyLinkedinUrl",
    "time_posted": "postedAt",
    "num_applicants": "applicantsCount",
    "recruiter_name": "jobPosterName",
    "recruiter_url": "jobPosterProfileUrl",
}

# Schema D: dataset_linkedin-jobs-scraper_02-49 / 03-07 (44 cols, comma)
SCHEMA_D = {
    "job_id": "job_urn",
    "job_title": "title",
    "company_name": "company_name",
    "job_description": "description_text",
    "location": "location",
    "salary_info": "base_salary",
    "seniority_level": "seniority_level",
    "employment_type": "employment_type",
    "work_type": None,
    "contract_type": None,
    "sector": "industries",
    "job_url": "job_url",
    "apply_url": "apply_url",
    "company_url": "company_profile",
    "time_posted": "posted_time_ago",
    "num_applicants": "applicants",
    "recruiter_name": "recruiter_name",
    "recruiter_url": "recruiter_profile",
}

# Schema E: jobs_consolidated (87 cols, semicolon)
SCHEMA_E = {
    "job_id": "linkedin_job_id",
    "job_title": "job_title",
    "company_name": "company_name",
    "job_description": "description",
    "location": "location",
    "salary_info": "salary",
    "seniority_level": "seniority_level",
    "employment_type": "employment_type",
    "work_type": None,
    "contract_type": None,
    "sector": "industries",
    "job_url": "job_url",
    "apply_url": "apply_url",
    "company_url": "company_url",
    "time_posted": "posted_time",
    "num_applicants": "applicants_count",
    "recruiter_name": None,
    "recruiter_url": None,
}


def detect_schema(filename, headers):
    """Detect which schema a file uses based on filename and headers."""
    header_set = set(headers)
    if "consolidated" in filename:
        return "E", SCHEMA_E
    if "jobId" in header_set and "jobTitle" in header_set:
        return "A", SCHEMA_A
    if "company/name" in header_set or "descriptionHtml" in header_set and "company/url" in header_set:
        return "B", SCHEMA_B
    if "companyName" in header_set and "seniorityLevel" in header_set:
        return "C", SCHEMA_C
    if "company_name" in header_set and ("job_urn" in header_set or "seniority_level" in header_set):
        return "D", SCHEMA_D
    # Fallback heuristics
    if len(headers) > 100:
        return "B", SCHEMA_B
    return "?", None


def extract_linkedin_id(raw_id, job_url=""):
    """Extract numeric LinkedIn job ID from various formats."""
    if raw_id:
        raw_id = str(raw_id).strip()
        # Direct numeric
        m = re.search(r'(\d{8,12})', raw_id)
        if m:
            return m.group(1)
    if job_url:
        job_url = str(job_url).strip()
        m = re.search(r'/view/(\d+)', job_url)
        if m:
            return m.group(1)
        m = re.search(r'currentJobId=(\d+)', job_url)
        if m:
            return m.group(1)
        m = re.search(r'(\d{8,12})', job_url)
        if m:
            return m.group(1)
    return None


def clean_text(val):
    """Clean a text value."""
    if val is None:
        return ""
    val = str(val).strip()
    if val.lower() in ("none", "nan", "null", "n/a", ""):
        return ""
    return val


def map_row(row_dict, mapping, source_file):
    """Map a raw CSV row to the target schema."""
    result = {}
    for target_col in TARGET_COLS:
        if target_col == "source_file":
            result[target_col] = source_file
            continue
        source_col = mapping.get(target_col)
        if source_col and source_col in row_dict:
            result[target_col] = clean_text(row_dict[source_col])
        else:
            result[target_col] = ""
    return result


def richness_score(row):
    """Count non-empty fields — used to pick the best duplicate."""
    return sum(1 for v in row.values() if v and str(v).strip())


def read_csv_file(filepath, filename):
    """Read a CSV file, auto-detect delimiter and schema, yield mapped rows."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()

    sep = ";" if first_line.count(";") > first_line.count(",") else ","

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=sep)
        # Clean header names
        if reader.fieldnames:
            reader.fieldnames = [h.strip().strip("\ufeff").strip('"') for h in reader.fieldnames]

        schema_name, mapping = detect_schema(filename, reader.fieldnames or [])
        if mapping is None:
            print(f"  [SKIP] Unknown schema for {filename}")
            return [], schema_name, 0

        row_count = 0
        rows = []
        for row in reader:
            row_count += 1
            mapped = map_row(row, mapping, filename)
            rows.append(mapped)

    return rows, schema_name, row_count


def main():
    print("=" * 70)
    print("  CSV MERGE ETL — LinkedIn Job Data Consolidation")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    csv_files = sorted([f for f in os.listdir(CSV_DIR) if f.endswith(".csv")])
    print(f"\nFound {len(csv_files)} CSV files\n")

    # ── Phase 1: Read & Normalize ──────────────────────────────────
    all_rows = []
    file_stats = []

    for fname in csv_files:
        path = os.path.join(CSV_DIR, fname)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"Reading: {fname} ({size_mb:.1f} MB)...", end=" ", flush=True)

        rows, schema, raw_count = read_csv_file(path, fname)
        mapped_count = len(rows)
        all_rows.extend(rows)

        print(f"Schema {schema} | {raw_count:,} rows read | {mapped_count:,} mapped")
        file_stats.append({
            "file": fname,
            "schema": schema,
            "size_mb": size_mb,
            "raw_rows": raw_count,
            "mapped_rows": mapped_count,
        })

    total_raw = len(all_rows)
    print(f"\n{'─'*70}")
    print(f"Phase 1 complete: {total_raw:,} total rows loaded")

    # ── Phase 2: Extract LinkedIn IDs ──────────────────────────────
    print(f"\nPhase 2: Extracting LinkedIn Job IDs...")
    no_id_count = 0
    synth_counter = 0
    for row in all_rows:
        lid = extract_linkedin_id(row.get("job_id", ""), row.get("job_url", ""))
        if lid:
            row["job_id"] = lid
        else:
            no_id_count += 1
            # Generate a synthetic ID for rows without a LinkedIn ID
            synth_counter += 1
            row["job_id"] = f"SYNTH_{synth_counter:07d}"

    print(f"  Real IDs extracted:  {total_raw - no_id_count:,}")
    print(f"  Synthetic IDs:       {synth_counter:,}")

    # ── Phase 3: Quality Filters ───────────────────────────────────
    print(f"\nPhase 3: Applying quality filters...")
    discard_reasons = Counter()
    valid_rows = []

    for row in all_rows:
        title = row.get("job_title", "").strip()
        company = row.get("company_name", "").strip()
        desc = row.get("job_description", "").strip()
        url = row.get("job_url", "").strip()

        if not title:
            discard_reasons["no_title"] += 1
            continue
        if not company:
            discard_reasons["no_company"] += 1
            continue
        if not desc and not url:
            discard_reasons["no_description_or_url"] += 1
            continue

        valid_rows.append(row)

    total_discarded = sum(discard_reasons.values())
    print(f"  Valid rows:    {len(valid_rows):,}")
    print(f"  Discarded:     {total_discarded:,}")
    for reason, count in discard_reasons.most_common():
        print(f"    - {reason}: {count:,}")

    # ── Phase 4: Deduplication ─────────────────────────────────────
    print(f"\nPhase 4: Deduplicating by LinkedIn Job ID...")
    id_groups = defaultdict(list)
    for row in valid_rows:
        id_groups[row["job_id"]].append(row)

    unique_rows = []
    dup_count = 0
    for jid, group in id_groups.items():
        if len(group) == 1:
            unique_rows.append(group[0])
        else:
            # Keep the richest record
            best = max(group, key=richness_score)
            unique_rows.append(best)
            dup_count += len(group) - 1

    print(f"  Unique jobs:   {len(unique_rows):,}")
    print(f"  Duplicates:    {dup_count:,}")

    # ── Phase 5: Write Output ──────────────────────────────────────
    print(f"\nPhase 5: Writing output CSV...")
    unique_rows.sort(key=lambda r: r.get("job_title", ""))

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_COLS)
        writer.writeheader()
        writer.writerows(unique_rows)

    output_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Size:   {output_size:.1f} MB")
    print(f"  Rows:   {len(unique_rows):,}")

    # -- Final Report -----------------------------------------------
    print(f"\n{'='*70}")
    print(f"  ETL REPORT -- FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"\n  INPUT FILES:")
    print(f"  {'File':<60} {'Schema':>6} {'Rows':>10}")
    print(f"  {'-'*60} {'-'*6} {'-'*10}")
    for s in file_stats:
        print(f"  {s['file']:<60} {s['schema']:>6} {s['raw_rows']:>10,}")
    print(f"  {'-'*60} {'-'*6} {'-'*10}")
    print(f"  {'TOTAL RAW':<60} {'':>6} {total_raw:>10,}")

    print(f"\n  PIPELINE:")
    print(f"  +-- Total rows loaded:       {total_raw:>10,}")
    print(f"  +-- Discarded (quality):    -{total_discarded:>10,}")
    for reason, count in discard_reasons.most_common():
        print(f"  |   +-- {reason:<22} {count:>10,}")
    print(f"  +-- After quality filter:    {len(valid_rows):>10,}")
    print(f"  +-- Duplicates removed:     -{dup_count:>10,}")
    print(f"  +-- FINAL CLEAN JOBS:        {len(unique_rows):>10,}")

    pct = (len(unique_rows) / total_raw * 100) if total_raw > 0 else 0
    print(f"\n  YIELD: {pct:.1f}% of raw input -> clean output")
    print(f"  OUTPUT: {OUTPUT_FILE}")
    print(f"  SIZE:   {output_size:.1f} MB")
    print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
