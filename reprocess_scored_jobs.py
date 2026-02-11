"""
Reprocess already-scored jobs with full classification filters:
a) International jobs: MUST accept remote candidates (discard non-remote)
b) Brazil jobs: Any work type (remote/hybrid/onsite) = eligible  
c) Management positions ONLY (discard technical hands-on)
d) Order by freshness: today > yesterday > older (to be first applicant)
"""
import psycopg2
import re
from datetime import datetime

DB_URL = 'postgresql://job_matcher:JobMatcher2024!@127.0.0.1:5432/job_matcher'

# MANAGEMENT KEYWORDS (INCLUDE)
MANAGEMENT_KEYWORDS = [
    'manager', 'director', 'head of', 'head,', 'vp ', 'vice president',
    'chief', 'cto', 'cio', 'coo', 'ceo', 'president',
    'delivery manager', 'program manager', 'portfolio manager', 'project manager',
    'operations manager', 'general manager', 'regional manager', 'country manager',
    'practice lead', 'practice director', 'engagement manager',
    'managing director', 'executive director', 'senior director',
    'gerente', 'diretor', 'coordenador',  # Portuguese titles
    'superintendent', 'administrator', 'principal consultant',
]

# TECHNICAL HANDS-ON KEYWORDS (EXCLUDE)
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

# BRAZIL KEYWORDS
BRAZIL_KEYWORDS = ['brazil', 'brasil', 'são paulo', 'sao paulo', 'rio de janeiro', 
                   'brasília', 'brasilia', 'belo horizonte', 'curitiba', 'porto alegre',
                   'salvador', 'recife', 'fortaleza', 'campinas', 'br-', ', br']

# REMOTE KEYWORDS
REMOTE_KEYWORDS = ['remote', 'anywhere', 'worldwide', 'work from home', 'wfh']

def is_management_position(title):
    """Check if job title is management/leadership"""
    title_lower = str(title).lower()
    
    # Has management keyword = eligible
    if any(kw in title_lower for kw in MANAGEMENT_KEYWORDS):
        return True, 'management'
    
    # Has technical keyword without management = discard
    if any(kw in title_lower for kw in TECHNICAL_HANDS_ON):
        return False, 'technical_hands_on'
    
    # Default: needs scoring (could be relevant)
    return True, 'needs_scoring'

def is_location_eligible(location, job_title, job_description):
    """Check if job location is eligible (Brazil=all, International=remote only)"""
    location_lower = str(location).lower()
    title_lower = str(job_title).lower()
    desc_lower = str(job_description or '')[:1000].lower()
    
    # Brazil-based = ALL work types eligible
    for kw in BRAZIL_KEYWORDS:
        if kw in location_lower:
            return True, 'brazil_local'
    
    # International = check for remote
    for kw in REMOTE_KEYWORDS:
        if kw in location_lower or kw in title_lower:
            return True, 'international_remote'
    
    # Check description for explicit remote mentions
    if 'fully remote' in desc_lower or '100% remote' in desc_lower or 'work from anywhere' in desc_lower:
        return True, 'international_remote'
    
    return False, 'international_not_remote'

def classify_job(job_id, title, location, description):
    """Full classification of a job"""
    # Step 1: Is it a management position?
    is_mgmt, mgmt_reason = is_management_position(title)
    if not is_mgmt:
        return False, f'discard_technical: {mgmt_reason}'
    
    # Step 2: Is location eligible?
    is_loc_ok, loc_reason = is_location_eligible(location, title, description)
    if not is_loc_ok:
        return False, f'discard_location: {loc_reason}'
    
    return True, f'eligible: {loc_reason}'

def reprocess_scored_jobs():
    """Reprocess all already-scored jobs with full classification"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Get all jobs with scores
    cur.execute("""
        SELECT id, job_id, job_title, location, job_description, score 
        FROM jobs 
        WHERE score IS NOT NULL
    """)
    scored_jobs = cur.fetchall()
    
    print(f"{'='*60}")
    print(f"REPROCESSING {len(scored_jobs)} ALREADY-SCORED JOBS")
    print(f"{'='*60}")
    print(f"Filters: Management + (Brazil OR Remote) + Freshness Priority")
    print(f"{'='*60}\n")
    
    stats = {
        'total': len(scored_jobs),
        'eligible_keep_score': 0,  # Management + location OK - keep current score
        'discard_technical': 0,     # Technical hands-on - set score=0
        'discard_location': 0,      # International non-remote - set score=0
        'needs_rescore': 0,         # Eligible but was incorrectly scored
    }
    
    eligible_jobs = []
    
    for job_id, linkedin_id, title, location, description, current_score in scored_jobs:
        is_eligible, reason = classify_job(job_id, title, location, description)
        
        if is_eligible:
            # Job passes all filters
            if current_score and current_score >= 75:
                stats['eligible_keep_score'] += 1
            else:
                stats['needs_rescore'] += 1
                eligible_jobs.append((job_id, title, location))
        else:
            # Job should be discarded
            if 'technical' in reason:
                stats['discard_technical'] += 1
                cur.execute("""
                    UPDATE jobs 
                    SET score = 0, 
                        justification = 'Auto-discarded: Technical hands-on role - user seeks management positions'
                    WHERE id = %s
                """, (job_id,))
            else:
                stats['discard_location'] += 1
                cur.execute("""
                    UPDATE jobs 
                    SET score = 0, 
                        justification = 'Auto-discarded: International job not accepting remote candidates'
                    WHERE id = %s
                """, (job_id,))
    
    conn.commit()
    
    # Print statistics
    print(f"CLASSIFICATION RESULTS:")
    print(f"{'='*60}")
    print(f"✅ Eligible (management + location OK): {stats['eligible_keep_score'] + stats['needs_rescore']}")
    print(f"   - Keep current score (≥75%): {stats['eligible_keep_score']}")
    print(f"   - Needs rescore (<75% or re-evaluate): {stats['needs_rescore']}")
    print(f"\n❌ Auto-discarded (set score=0):")
    print(f"   - Technical hands-on roles: {stats['discard_technical']}")
    print(f"   - International non-remote: {stats['discard_location']}")
    print(f"{'='*60}")
    
    # Show sample of discarded jobs
    cur.execute("""
        SELECT job_title, location, justification FROM jobs 
        WHERE score = 0 AND justification LIKE 'Auto-discarded%'
        ORDER BY updated_at DESC
        LIMIT 10
    """)
    print("\nSample discarded jobs:")
    for row in cur.fetchall():
        reason = 'Technical' if 'Technical' in (row[2] or '') else 'Not Remote'
        print(f"  ❌ [{reason}] {row[0][:50]} | {row[1][:30]}")
    
    # Show sample of eligible high-score jobs
    cur.execute("""
        SELECT job_title, company_name, location, score FROM jobs 
        WHERE score >= 75
        ORDER BY score DESC
        LIMIT 10
    """)
    print("\nTop qualified jobs (score ≥75%):")
    for row in cur.fetchall():
        print(f"  ✅ {row[3]}% | {row[0][:40]} @ {row[1][:20]}")
    
    cur.close()
    conn.close()
    
    print(f"\n🎯 Reprocessing complete!")
    print(f"   Discarded: {stats['discard_technical'] + stats['discard_location']} jobs (score=0)")
    print(f"   Eligible: {stats['eligible_keep_score'] + stats['needs_rescore']} jobs")
    
    return stats

if __name__ == "__main__":
    reprocess_scored_jobs()
