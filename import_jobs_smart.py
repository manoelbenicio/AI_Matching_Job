"""
Intelligent Job Import with Remote Filter + Freshness Priority
- Brazil-based jobs: ALL eligible (remote, onsite, hybrid)
- International jobs: ONLY remote eligible
- Auto-discards non-eligible jobs (no API cost)
- Prioritizes by freshness: today > yesterday > older
- Sends Telegram notifications for qualified jobs
"""
import pandas as pd
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_URL = os.getenv('DATABASE_URL', 'postgresql://job_matcher:JobMatcher2024!@127.0.0.1:5432/job_matcher')

def parse_posted_date(posted_str):
    """Convert LinkedIn posted_date to days_ago integer for sorting"""
    if pd.isna(posted_str):
        return 999  # Unknown = lowest priority
    
    posted_str = str(posted_str).lower().strip()
    
    # Handle relative dates
    if 'hour' in posted_str or 'minute' in posted_str:
        return 0  # Today
    elif '1 day' in posted_str:
        return 1
    elif '2 day' in posted_str:
        return 2
    elif '3 day' in posted_str:
        return 3
    elif '4 day' in posted_str:
        return 4
    elif '5 day' in posted_str:
        return 5
    elif '6 day' in posted_str:
        return 6
    elif '1 week' in posted_str:
        return 7
    elif '2 week' in posted_str:
        return 14
    elif '3 week' in posted_str:
        return 21
    elif 'month' in posted_str:
        return 30
    else:
        # Try to parse ISO date
        try:
            dt = pd.to_datetime(posted_str)
            days_ago = (datetime.now() - dt.replace(tzinfo=None)).days
            return max(0, days_ago)
        except:
            return 999

def is_management_position(title):
    """
    Check if job title is a management/leadership position.
    User has 20+ years management experience - NOT interested in hands-on technical roles.
    
    INCLUDE: Manager, Director, Head, VP, Lead (management), Principal (management)
    EXCLUDE: Software Engineer, Developer, Programmer, Data Scientist (hands-on technical)
    """
    title_lower = str(title).lower()
    
    # MANAGEMENT/LEADERSHIP KEYWORDS (INCLUDE)
    management_keywords = [
        'manager', 'director', 'head of', 'head,', 'vp ', 'vice president',
        'chief', 'cto', 'cio', 'coo', 'ceo', 'president',
        'delivery manager', 'program manager', 'portfolio manager', 'project manager',
        'operations manager', 'general manager', 'regional manager', 'country manager',
        'practice lead', 'practice director', 'engagement manager',
        'managing director', 'executive director', 'senior director',
        'gerente', 'diretor', 'coordenador',  # Portuguese titles
        'superintendent', 'administrator', 'principal consultant',
    ]
    
    # Check if title contains management keywords
    has_management_title = any(kw in title_lower for kw in management_keywords)
    
    # HANDS-ON TECHNICAL KEYWORDS (EXCLUDE unless also has management keyword)
    technical_hands_on = [
        'software engineer', 'senior software engineer', 'staff engineer',
        'developer', 'programmer', 'coder',
        'data scientist', 'data engineer', 'ml engineer', 'machine learning engineer',
        'devops engineer', 'sre', 'site reliability', 'platform engineer',
        'backend engineer', 'frontend engineer', 'full stack engineer', 'fullstack engineer',
        'qa engineer', 'test engineer', 'automation engineer',
        'cloud engineer', 'infrastructure engineer', 'network engineer',
        'security engineer', 'sdet', 'solutions engineer',
        'architect',  # Usually hands-on unless "Enterprise Architect" or similar
    ]
    
    # Check if it's a pure technical role (no management aspect)
    is_pure_technical = any(kw in title_lower for kw in technical_hands_on)
    
    # If has management keyword, it's eligible (even if also has technical terms)
    if has_management_title:
        return True, 'management'
    
    # If pure technical with no management aspect, not eligible
    if is_pure_technical:
        return False, 'technical_hands_on'
    
    # Default: allow scoring (AI will determine fit based on full context)
    return True, 'needs_scoring'

def is_eligible_job(row):
    """
    Check if job is eligible for scoring (user based in São Paulo, Brazil):
    1. Must be MANAGEMENT position (20+ years management experience)
    2. Brazil-based jobs: ALL work types eligible
    3. International jobs: ONLY remote eligible
    """
    title = row.get('job_title', '')
    location = str(row.get('location', '')).lower()
    
    # FIRST CHECK: Is it a management position?
    is_mgmt, mgmt_reason = is_management_position(title)
    if not is_mgmt:
        return False, f'not_management_{mgmt_reason}'
    
    # SECOND CHECK: Location/remote eligibility
    # Brazil-based jobs are ALL eligible (user can work onsite/hybrid in Brazil)
    brazil_keywords = ['brazil', 'brasil', 'são paulo', 'sao paulo', 'rio de janeiro', 
                       'brasília', 'brasilia', 'belo horizonte', 'curitiba', 'porto alegre',
                       'salvador', 'recife', 'fortaleza', 'campinas', 'br-', ', br']
    for kw in brazil_keywords:
        if kw in location:
            return True, 'brazil_local_management'
    
    # International jobs: check if remote
    # Check remote_allowed flag
    if pd.notna(row.get('remote_allowed')) and row['remote_allowed'] == 1:
        return True, 'remote_management'
    
    # Check work_type
    work_type = str(row.get('work_type', '')).lower()
    if 'remote' in work_type:
        return True, 'remote_management'
    
    # Check location for remote keywords
    if 'remote' in location or 'anywhere' in location or 'worldwide' in location:
        return True, 'remote_management'
    
    # Check job title for remote
    if 'remote' in str(title).lower():
        return True, 'remote_management'
    
    # Check description for explicit remote mentions
    desc = str(row.get('description', '')).lower()[:500]
    if 'fully remote' in desc or '100% remote' in desc or 'work from anywhere' in desc:
        return True, 'remote_management'
    
    return False, 'not_remote_international'

def import_jobs_with_priority():
    """Import jobs with remote filter and freshness priority"""
    
    # Load Excel
    excel_path = r'D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\Jobs_Linkedin_PROD_8_2_2026.xlsx'
    print(f"Loading jobs from: {excel_path}")
    df = pd.read_excel(excel_path)
    
    total_jobs = len(df)
    print(f"Total jobs in Excel: {total_jobs}")
    
    # Calculate days_ago for sorting
    df['days_ago'] = df['posted_date'].apply(parse_posted_date)
    
    # Classify eligible vs non-eligible
    eligibility_results = df.apply(is_eligible_job, axis=1)
    df['is_eligible'] = eligibility_results.apply(lambda x: x[0])
    df['eligibility_reason'] = eligibility_results.apply(lambda x: x[1])
    
    eligible_jobs = df[df['is_eligible'] == True].copy()
    non_eligible_jobs = df[df['is_eligible'] == False].copy()
    
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION RESULTS (User in São Paulo, Brazil):")
    print(f"{'='*60}")
    print(f"✅ ELIGIBLE jobs (MANAGEMENT + Location OK): {len(eligible_jobs)}")
    
    # Show breakdown by eligibility reason
    for reason in eligible_jobs['eligibility_reason'].unique():
        count = len(eligible_jobs[eligible_jobs['eligibility_reason'] == reason])
        print(f"   - {reason}: {count}")
    
    print(f"\n❌ NON-ELIGIBLE (auto-discarded): {len(non_eligible_jobs)}")
    
    # Show breakdown of rejection reasons
    for reason in non_eligible_jobs['eligibility_reason'].unique():
        count = len(non_eligible_jobs[non_eligible_jobs['eligibility_reason'] == reason])
        print(f"   - {reason}: {count}")
    print(f"{'='*60}")

    
    # Sort eligible jobs by freshness (days_ago ascending = freshest first)
    eligible_jobs = eligible_jobs.sort_values('days_ago')
    
    # Show freshness distribution
    print(f"\nELIGIBLE JOBS BY FRESHNESS:")
    freshness_dist = eligible_jobs['days_ago'].value_counts().sort_index()
    for days, count in freshness_dist.head(10).items():
        label = "today" if days == 0 else f"{days} day(s) ago"
        print(f"  {label}: {count} jobs")
    
    # Connect to database
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Get existing job IDs to avoid duplicates (using job_id column which is varchar)
    cur.execute("SELECT job_id FROM jobs WHERE job_id IS NOT NULL")
    existing_ids = set(str(r[0]) for r in cur.fetchall())
    print(f"\nExisting jobs in database: {len(existing_ids)}")
    
    # Prepare inserts
    eligible_to_insert = []
    discarded_to_insert = []
    
    for _, row in eligible_jobs.iterrows():
        linkedin_id = str(row.get('linkedin_job_id', ''))
        if linkedin_id and linkedin_id not in existing_ids:
            eligible_to_insert.append({
                'job_id': linkedin_id,
                'job_title': row.get('job_title', ''),
                'company_name': row.get('company_name', ''),
                'location': row.get('location', ''),
                'job_description': row.get('description', ''),
                'job_url': row.get('job_url', ''),
                'seniority_level': row.get('seniority_level', ''),
                'salary_info': row.get('salary', ''),
                'days_ago': row.get('days_ago', 999),
                'eligibility_reason': row.get('eligibility_reason', ''),
            })
    
    for _, row in non_eligible_jobs.iterrows():
        linkedin_id = str(row.get('linkedin_job_id', ''))
        if linkedin_id and linkedin_id not in existing_ids:
            discarded_to_insert.append({
                'job_id': linkedin_id,
                'job_title': row.get('job_title', ''),
                'company_name': row.get('company_name', ''),
                'location': row.get('location', ''),
                'job_description': row.get('description', ''),
                'job_url': row.get('job_url', ''),
            })
    
    print(f"\nNEW JOBS TO INSERT:")
    print(f"  ✅ Eligible jobs (to be scored): {len(eligible_to_insert)}")
    print(f"  ❌ Non-eligible (auto-discarded): {len(discarded_to_insert)}")
    
    # Insert eligible jobs (pending scoring) - prioritized by freshness
    inserted_count = 0
    if eligible_to_insert:
        insert_sql = """
            INSERT INTO jobs (job_id, job_title, company_name, location, 
                            job_description, job_url, seniority_level, salary_info, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (job_id) DO NOTHING
        """
        
        # Sort by days_ago before inserting (freshest first)
        eligible_to_insert.sort(key=lambda x: x['days_ago'])
        
        for job in eligible_to_insert:
            try:
                cur.execute(insert_sql, (
                    job['job_id'],
                    str(job['job_title'])[:500] if job['job_title'] else '',
                    str(job['company_name'])[:200] if job['company_name'] else '',
                    str(job['location'])[:200] if job['location'] else '',
                    str(job['job_description'])[:10000] if job['job_description'] else '',
                    str(job['job_url'])[:500] if job['job_url'] else '',
                    str(job['seniority_level'])[:100] if job['seniority_level'] else '',
                    str(job['salary_info'])[:100] if job['salary_info'] else '',
                ))
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting {job['job_id']}: {e}")
        
        conn.commit()
        print(f"\n✅ Inserted {inserted_count} eligible jobs (freshest first)")
    
    # Insert discarded jobs with score=0 and justification
    discarded_count = 0
    if discarded_to_insert:
        insert_discarded_sql = """
            INSERT INTO jobs (job_id, job_title, company_name, location,
                            job_description, job_url, score, justification, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 'Auto-discarded: Not remote (user based in Brazil)', NOW())
            ON CONFLICT (job_id) DO NOTHING
        """
        
        for job in discarded_to_insert:
            try:
                cur.execute(insert_discarded_sql, (
                    job['job_id'],
                    str(job['job_title'])[:500] if job['job_title'] else '',
                    str(job['company_name'])[:200] if job['company_name'] else '',
                    str(job['location'])[:200] if job['location'] else '',
                    str(job['job_description'])[:10000] if job['job_description'] else '',
                    str(job['job_url'])[:500] if job['job_url'] else '',
                ))
                discarded_count += 1
            except Exception as e:
                pass  # Ignore duplicates
        
        conn.commit()
        print(f"❌ Recorded {discarded_count} discarded non-remote jobs (score=0)")
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"Ready to score {inserted_count} eligible jobs by freshness")
    print(f"Saved OpenAI API costs on {discarded_count} non-remote international jobs")
    
    return inserted_count, discarded_count

if __name__ == "__main__":
    import_jobs_with_priority()
