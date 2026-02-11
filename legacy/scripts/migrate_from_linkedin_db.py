#!/usr/bin/env python3
"""
Migrate data from linkedin_jobs_db to job_matcher database
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Source database (linkedin_jobs_db on port 5433)
SOURCE_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'dbname': 'linkedin_jobs',
    'user': 'n8n_user',
    'password': 'n8n_secure_pass_2024'
}

# Target database (job_matcher on port 5432)
TARGET_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'job_matcher',
    'user': 'job_matcher',
    'password': 'JobMatcher2024!'
}


def map_status(job_state, score):
    if score is not None and score >= 75:
        return 'qualified'
    elif score is not None:
        return 'low_score'
    elif job_state == 'processed':
        return 'qualified'
    elif job_state == 'error':
        return 'error'
    else:
        return 'pending'


def migrate():
    print("Connecting to source database...")
    source_conn = psycopg2.connect(**SOURCE_CONFIG)
    source_cur = source_conn.cursor(cursor_factory=RealDictCursor)
    
    print("Connecting to target database...")
    target_conn = psycopg2.connect(**TARGET_CONFIG)
    target_cur = target_conn.cursor()
    
    # Fetch all jobs from source
    print("Fetching jobs from linkedin_jobs_db...")
    source_cur.execute("""
        SELECT 
            linkedin_job_id,
            job_title,
            company_name,
            description,
            location,
            salary,
            seniority_level,
            employment_type,
            posted_at,
            applicants_count,
            job_url,
            apply_url,
            match_score,
            ai_match_reasons,
            matched_resume_url,
            processed_at,
            job_state,
            ai_evaluation_raw
        FROM linkedin_jobs
        WHERE linkedin_job_id IS NOT NULL
    """)
    
    jobs = source_cur.fetchall()
    print(f"Found {len(jobs)} jobs to migrate")
    
    migrated = 0
    skipped = 0
    errors = []
    
    for i, job in enumerate(jobs):
        try:
            # Convert job_id to string, handle floats
            job_id = job['linkedin_job_id']
            if job_id:
                job_id = str(job_id).replace('.0', '')
            
            target_cur.execute("""
                INSERT INTO jobs (
                    job_id, job_title, company_name, job_description,
                    location, salary_info, seniority_level, employment_type,
                    time_posted, applicants_count, job_url, apply_url,
                    score, justification, custom_resume_url, status,
                    processed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (job_id) DO NOTHING
            """, (
                job_id,
                job['job_title'],
                job['company_name'],
                job['description'],
                job['location'],
                job['salary'],
                job['seniority_level'],
                job['employment_type'],
                str(job['posted_at']) if job['posted_at'] else None,
                job['applicants_count'],
                job['job_url'],
                job['apply_url'],
                job['match_score'],
                job['ai_match_reasons'],
                job['matched_resume_url'],
                map_status(job['job_state'], job['match_score']),
                job['processed_at']
            ))
            target_conn.commit()
            migrated += 1
            
            if (i + 1) % 500 == 0:
                print(f"  Progress: {i + 1}/{len(jobs)} ({migrated} migrated)")
                
        except Exception as e:
            target_conn.rollback()
            if len(errors) < 3:
                errors.append(f"{job.get('linkedin_job_id')}: {str(e)[:100]}")
            skipped += 1
    
    print(f"\nMigration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    
    if errors:
        print(f"\nSample errors:")
        for err in errors:
            print(f"  {err}")
    
    # Show summary
    target_cur.execute("""
        SELECT status, COUNT(*) as count 
        FROM jobs 
        GROUP BY status 
        ORDER BY count DESC
    """)
    print("\nTarget database summary:")
    for row in target_cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    source_conn.close()
    target_conn.close()


if __name__ == '__main__':
    migrate()
