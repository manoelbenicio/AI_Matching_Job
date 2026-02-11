"""
Auto-discard technical hands-on jobs already in the database.
User has 20+ years management experience - only wants leadership roles.
"""
import psycopg2
import re

DB_URL = 'postgresql://job_matcher:JobMatcher2024!@127.0.0.1:5432/job_matcher'

# Technical hands-on keywords to auto-discard
TECHNICAL_HANDS_ON = [
    'software engineer', 'senior software engineer', 'staff engineer',
    'developer', 'programmer', 'coder',
    'data scientist', 'data engineer', 'ml engineer', 'machine learning engineer',
    'devops engineer', 'sre', 'site reliability', 'platform engineer',
    'backend engineer', 'frontend engineer', 'full stack engineer', 'fullstack engineer',
    'qa engineer', 'test engineer', 'automation engineer',
    'cloud engineer', 'infrastructure engineer', 'network engineer',
    'security engineer', 'sdet', 'solutions engineer',
]

# Management keywords that make a job eligible even if it has technical terms
MANAGEMENT_KEYWORDS = [
    'manager', 'director', 'head', 'vp', 'vice president',
    'chief', 'cto', 'cio', 'coo', 'ceo', 'president',
    'gerente', 'diretor', 'coordenador',
]

def is_technical_not_management(title):
    """Check if title is technical without management aspect"""
    title_lower = title.lower()
    
    # Has management keyword = keep
    if any(kw in title_lower for kw in MANAGEMENT_KEYWORDS):
        return False
    
    # Has technical keyword without management = discard
    if any(kw in title_lower for kw in TECHNICAL_HANDS_ON):
        return True
    
    return False

def discard_technical_jobs():
    """Mark technical hands-on jobs as discarded (score=0)"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Get all pending jobs (no score yet)
    cur.execute("SELECT id, job_title FROM jobs WHERE score IS NULL")
    pending_jobs = cur.fetchall()
    
    print(f"Total pending jobs: {len(pending_jobs)}")
    
    technical_count = 0
    management_count = 0
    
    for job_id, title in pending_jobs:
        if is_technical_not_management(title):
            # Auto-discard with score 0
            cur.execute("""
                UPDATE jobs 
                SET score = 0, 
                    justification = 'Auto-discarded: Technical hands-on role (user seeks management positions only)'
                WHERE id = %s
            """, (job_id,))
            technical_count += 1
        else:
            management_count += 1
    
    conn.commit()
    
    print(f"\n{'='*60}")
    print(f"AUTO-DISCARD RESULTS:")
    print(f"{'='*60}")
    print(f"❌ Technical hands-on discarded: {technical_count}")
    print(f"✅ Management/other (need scoring): {management_count}")
    print(f"{'='*60}")
    
    # Show sample of discarded titles
    cur.execute("""
        SELECT job_title FROM jobs 
        WHERE justification LIKE '%Technical hands-on%' 
        LIMIT 10
    """)
    print("\nSample discarded technical jobs:")
    for row in cur.fetchall():
        print(f"  ❌ {row[0][:70]}")
    
    # Show sample of remaining management jobs
    cur.execute("""
        SELECT job_title, company_name FROM jobs 
        WHERE score IS NULL 
        LIMIT 10
    """)
    print("\nSample remaining management jobs to score:")
    for row in cur.fetchall():
        print(f"  ✅ {row[0][:50]} @ {row[1][:25]}")
    
    cur.close()
    conn.close()
    
    return management_count

if __name__ == "__main__":
    remaining = discard_technical_jobs()
    print(f"\n🎯 Ready to score {remaining} management positions!")
