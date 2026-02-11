#!/usr/bin/env python3
"""
Import Google Sheets jobs data into PostgreSQL

Usage:
    python import_sheets_to_postgres.py --spreadsheet-id YOUR_SHEET_ID --credentials creds.json

Requirements:
    pip install psycopg2-binary google-api-python-client google-auth-oauthlib
"""

import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Any

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Please install psycopg2: pip install psycopg2-binary")
    exit(1)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("Please install Google API: pip install google-api-python-client google-auth-oauthlib")
    exit(1)


# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'job_matcher'),
    'user': os.getenv('DB_USER', 'job_matcher'),
    'password': os.getenv('DB_PASSWORD', 'JobMatcher2024!')
}

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_sheets_service(credentials_file: str) -> Any:
    """Authenticate with Google Sheets API"""
    creds = None
    token_file = 'token.json'
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return build('sheets', 'v4', credentials=creds)


def fetch_sheet_data(service: Any, spreadsheet_id: str, range_name: str = 'input!A:Z') -> List[Dict]:
    """Fetch all data from Google Sheet"""
    print(f"Fetching data from spreadsheet: {spreadsheet_id}")
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    rows = result.get('values', [])
    if not rows:
        print("No data found in spreadsheet")
        return []
    
    # First row is headers
    headers = [h.lower().replace(' ', '_') for h in rows[0]]
    
    # Convert rows to dictionaries
    data = []
    for row in rows[1:]:
        # Pad row to match headers length
        row_padded = row + [''] * (len(headers) - len(row))
        record = dict(zip(headers, row_padded))
        data.append(record)
    
    print(f"Found {len(data)} records")
    return data


def import_to_postgres(data: List[Dict], conn: Any) -> int:
    """Import data into PostgreSQL jobs table"""
    if not data:
        return 0
    
    cursor = conn.cursor()
    imported = 0
    
    for record in data:
        try:
            # Map sheet columns to database columns
            job_id = record.get('job_id') or record.get('linkedin_job_id') or record.get('id', '')
            if not job_id:
                continue
            
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, job_title, company_name, job_description, location,
                    salary_info, work_type, contract_type, seniority_level, sector,
                    job_url, apply_url, company_url, time_posted,
                    num_applicants, recruiter_name, recruiter_url,
                    status, score, justification, custom_resume_url,
                    scored_at, processed_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (job_id) DO UPDATE SET
                    job_title = EXCLUDED.job_title,
                    company_name = EXCLUDED.company_name,
                    job_description = EXCLUDED.job_description,
                    status = COALESCE(EXCLUDED.status, jobs.status),
                    score = COALESCE(EXCLUDED.score, jobs.score),
                    justification = COALESCE(EXCLUDED.justification, jobs.justification),
                    custom_resume_url = COALESCE(EXCLUDED.custom_resume_url, jobs.custom_resume_url),
                    updated_at = NOW()
            """, (
                job_id,
                record.get('job_title', ''),
                record.get('company_name', ''),
                record.get('job_description', ''),
                record.get('location', ''),
                record.get('salary_info') or record.get('salary_range', ''),
                record.get('work_type', ''),
                record.get('contract_type', ''),
                record.get('experience_level') or record.get('seniority_level', ''),
                record.get('sector', ''),
                record.get('job_url', ''),
                record.get('apply_url', ''),
                record.get('company_url', ''),
                record.get('time_posted') or record.get('posted_time', ''),
                record.get('num_applicants') or record.get('applicants_count', ''),
                record.get('recruiter_name', ''),
                record.get('recruiter_url', ''),
                record.get('status', 'pending'),
                int(record.get('score', 0)) if record.get('score') else None,
                record.get('justification') or record.get('score_justification', ''),
                record.get('custom_resume_url', ''),
                datetime.fromisoformat(record.get('scored_at')) if record.get('scored_at') else None,
                datetime.fromisoformat(record.get('processed_at')) if record.get('processed_at') else None
            ))
            imported += 1
            
        except Exception as e:
            print(f"Error importing record {job_id}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    return imported


def main():
    parser = argparse.ArgumentParser(description='Import Google Sheets data to PostgreSQL')
    parser.add_argument('--spreadsheet-id', required=True, help='Google Spreadsheet ID')
    parser.add_argument('--credentials', default='credentials.json', help='Google credentials file')
    parser.add_argument('--range', default='input!A:Z', help='Sheet range to import')
    parser.add_argument('--db-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--db-name', default='job_matcher', help='Database name')
    parser.add_argument('--db-user', default='job_matcher', help='Database user')
    parser.add_argument('--db-password', default='JobMatcher2024!', help='Database password')
    
    args = parser.parse_args()
    
    # Update DB config from args
    DB_CONFIG.update({
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    })
    
    print("=" * 60)
    print("Google Sheets to PostgreSQL Importer")
    print("=" * 60)
    
    # Connect to Google Sheets
    print("\n1. Connecting to Google Sheets...")
    service = get_sheets_service(args.credentials)
    
    # Fetch data
    print("\n2. Fetching sheet data...")
    data = fetch_sheet_data(service, args.spreadsheet_id, args.range)
    
    if not data:
        print("No data to import. Exiting.")
        return
    
    # Connect to PostgreSQL
    print(f"\n3. Connecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("   Connected successfully!")
    except Exception as e:
        print(f"   Failed to connect: {e}")
        return
    
    # Import data
    print("\n4. Importing data...")
    imported = import_to_postgres(data, conn)
    
    print(f"\n{'=' * 60}")
    print(f"Import complete! {imported} records imported/updated.")
    print(f"{'=' * 60}")
    
    # Show summary
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM jobs 
        GROUP BY status 
        ORDER BY COUNT(*) DESC
    """)
    print("\nStatus Distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()


if __name__ == '__main__':
    main()
