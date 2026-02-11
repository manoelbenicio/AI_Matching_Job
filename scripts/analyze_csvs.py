"""Analyze CSV files in migrations/CSV — headers, row counts, delimiters."""
import os, csv

CSV_DIR = r"D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\migrations\CSV"

for fname in sorted(os.listdir(CSV_DIR)):
    if not fname.endswith(".csv"):
        continue
    path = os.path.join(CSV_DIR, fname)
    size_mb = os.path.getsize(path) / (1024*1024)
    
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
    
    # Detect delimiter
    sep = ";" if first.count(";") > first.count(",") else ","
    
    # Parse header
    headers = [h.strip().strip("\ufeff").strip('"') for h in first.split(sep)]
    
    # Count rows (fast)
    with open(path, "rb") as f:
        row_count = sum(1 for _ in f) - 1  # subtract header
    
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    print(f"SIZE: {size_mb:.1f} MB | ROWS: {row_count:,} | SEP: {repr(sep)} | COLS: {len(headers)}")
    print(f"HEADERS:")
    for i, h in enumerate(headers):
        print(f"  [{i:2d}] {h}")
