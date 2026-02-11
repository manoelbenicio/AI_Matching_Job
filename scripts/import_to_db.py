"""
Import jobs_merged_final.csv into the Postgres jobs table.

Reads the merged CSV and inserts rows into the `jobs` table using
psycopg2 with batch inserts for performance.
"""
import csv
import os
import sys
import time

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Installing psycopg2-binary...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary -q")
    import psycopg2
    from psycopg2.extras import execute_values

CSV_FILE = r"D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\migrations\jobs_merged_final.csv"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "job_matcher",
    "user": "job_matcher",
    "password": "JobMatcher2024!",
}

# Map CSV columns to DB columns
INSERT_COLS = [
    "job_id",
    "job_title",
    "company_name",
    "job_description",
    "location",
    "salary_info",
    "seniority_level",
    "employment_type",
    "work_type",
    "contract_type",
    "sector",
    "job_url",
    "apply_url",
    "company_url",
    "time_posted",
    "num_applicants",
    "recruiter_name",
    "recruiter_url",
]

BATCH_SIZE = 500


def clean_val(val, max_len=None):
    """Clean a string value for DB insertion."""
    if val is None or str(val).strip() in ("", "None", "nan", "null", "N/A"):
        return None
    val = str(val).strip()
    if max_len and len(val) > max_len:
        val = val[:max_len]
    return val


def parse_applicants(val):
    """Try to extract an integer applicants count."""
    if not val:
        return None, None
    val = str(val).strip()
    import re
    m = re.search(r'(\d[\d,]*)', val)
    if m:
        num = int(m.group(1).replace(",", ""))
        return val, num
    return val, None


def main():
    print("=" * 60)
    print("  CSV -> Postgres Import")
    print("=" * 60)

    # Connect
    print(f"\nConnecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # Check current count
    cur.execute("SELECT COUNT(*) FROM jobs")
    existing = cur.fetchone()[0]
    print(f"  Existing rows in jobs table: {existing}")

    if existing > 0:
        print(f"  WARNING: Table is not empty. Truncating...")
        cur.execute("TRUNCATE TABLE jobs RESTART IDENTITY CASCADE")
        conn.commit()
        print(f"  Table truncated.")

    # Read CSV
    print(f"\nReading CSV: {CSV_FILE}")
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"  Rows in CSV: {len(rows):,}")

    # Prepare INSERT
    col_names = ", ".join(INSERT_COLS)
    placeholders = ", ".join(["%s"] * len(INSERT_COLS))
    insert_sql = f"""
        INSERT INTO jobs ({col_names})
        VALUES %s
        ON CONFLICT (job_id) DO NOTHING
    """

    # Build value tuples
    print(f"\nInserting into database (batch size: {BATCH_SIZE})...")
    start_time = time.time()
    inserted = 0
    skipped = 0
    errors = 0

    batch = []
    for i, row in enumerate(rows):
        num_applicants_str, applicants_count = parse_applicants(row.get("num_applicants", ""))

        values = (
            clean_val(row.get("job_id"), 100),           # job_id
            clean_val(row.get("job_title"), 500),         # job_title
            clean_val(row.get("company_name"), 500),      # company_name
            clean_val(row.get("job_description")),        # job_description
            clean_val(row.get("location"), 500),          # location
            clean_val(row.get("salary_info"), 255),       # salary_info
            clean_val(row.get("seniority_level"), 100),   # seniority_level
            clean_val(row.get("employment_type"), 100),   # employment_type
            clean_val(row.get("work_type"), 100),         # work_type
            clean_val(row.get("contract_type"), 100),     # contract_type
            clean_val(row.get("sector"), 255),            # sector
            clean_val(row.get("job_url")),                # job_url
            clean_val(row.get("apply_url")),              # apply_url
            clean_val(row.get("company_url")),            # company_url
            clean_val(row.get("time_posted"), 100),       # time_posted
            num_applicants_str,                           # num_applicants
            clean_val(row.get("recruiter_name"), 255),    # recruiter_name
            clean_val(row.get("recruiter_url")),          # recruiter_url
        )
        batch.append(values)

        if len(batch) >= BATCH_SIZE:
            try:
                execute_values(cur, insert_sql, batch, template=f"({placeholders})")
                inserted += len(batch)
            except Exception as e:
                conn.rollback()
                errors += len(batch)
                print(f"  ERROR at batch {i // BATCH_SIZE}: {e}")
            batch = []

            if (i + 1) % 2000 == 0:
                conn.commit()
                elapsed = time.time() - start_time
                rate = inserted / elapsed if elapsed > 0 else 0
                print(f"  Progress: {inserted:,} inserted ({rate:.0f} rows/sec)")

    # Final batch
    if batch:
        try:
            execute_values(cur, insert_sql, batch, template=f"({placeholders})")
            inserted += len(batch)
        except Exception as e:
            conn.rollback()
            errors += len(batch)
            print(f"  ERROR in final batch: {e}")

    conn.commit()
    elapsed = time.time() - start_time

    # Verify
    cur.execute("SELECT COUNT(*) FROM jobs")
    final_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    # Report
    print(f"\n{'='*60}")
    print(f"  IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"  CSV rows:        {len(rows):>10,}")
    print(f"  Inserted:        {inserted:>10,}")
    print(f"  Errors:          {errors:>10,}")
    print(f"  DB total rows:   {final_count:>10,}")
    print(f"  Time:            {elapsed:>10.1f}s")
    print(f"  Rate:            {inserted/elapsed:>10.0f} rows/sec")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
