#!/usr/bin/env python3
"""
Excel Export Utility
====================
Export qualified jobs to Excel for review

Usage:
    python export_to_excel.py                    # Export all qualified jobs
    python export_to_excel.py --status enhanced  # Export enhanced only
    python export_to_excel.py --min-score 80     # Export 80%+ only
"""

import os
import sys
import argparse
from datetime import datetime

try:
    import pandas as pd
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Install dependencies: pip install pandas psycopg2-binary openpyxl")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        dbname=os.getenv('DB_NAME', 'job_matcher'),
        user=os.getenv('DB_USER', 'job_matcher'),
        password=os.getenv('DB_PASSWORD', 'JobMatcher2024!')
    )


def export_jobs(
    output_file: str,
    status: str = None,
    min_score: int = 0,
    limit: int = 1000
) -> int:
    """Export jobs to Excel file"""
    
    conn = get_connection()
    
    # Build query
    conditions = ["score IS NOT NULL"]
    params = []
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    else:
        conditions.append("status IN ('qualified', 'enhanced')")
    
    if min_score > 0:
        conditions.append("score >= %s")
        params.append(min_score)
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT 
            job_id,
            job_title,
            company_name,
            score,
            justification,
            status,
            job_url,
            apply_url,
            custom_resume_url,
            location,
            salary_info,
            seniority_level,
            work_type,
            time_posted,
            num_applicants,
            scored_at,
            processed_at
        FROM jobs
        WHERE {where_clause}
        ORDER BY score DESC, processed_at DESC
        LIMIT %s
    """
    params.append(limit)
    
    # Fetch data
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        print("No jobs found matching criteria")
        return 0
    
    # Format columns
    df['score'] = df['score'].apply(lambda x: f"{x}%")
    
    # Create clickable links
    for col in ['job_url', 'apply_url', 'custom_resume_url']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if pd.notna(x) and x else '')
    
    # Rename columns for display
    df.columns = [col.replace('_', ' ').title() for col in df.columns]
    
    # Export to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Qualified Jobs')
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Qualified Jobs']
        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + i)].width = min(max_len, 50)
    
    print(f"Exported {len(df)} jobs to {output_file}")
    return len(df)


def main():
    parser = argparse.ArgumentParser(description='Export jobs to Excel')
    parser.add_argument('--output', '-o', default=None,
                       help='Output file path')
    parser.add_argument('--status', '-s', 
                       choices=['qualified', 'enhanced', 'low_score', 'all'],
                       help='Filter by status')
    parser.add_argument('--min-score', type=int, default=0,
                       help='Minimum score threshold')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Maximum rows to export')
    
    args = parser.parse_args()
    
    # Generate output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'qualified_jobs_{timestamp}.xlsx'
    
    status = None if args.status == 'all' else args.status
    
    export_jobs(
        output_file=args.output,
        status=status,
        min_score=args.min_score,
        limit=args.limit
    )


if __name__ == '__main__':
    main()
