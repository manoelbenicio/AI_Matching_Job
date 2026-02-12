"""
Pre-filter ALL jobs with rule-based classification:
a) International jobs: MUST accept remote candidates (discard non-remote)
b) Brazil jobs: Any work type (remote/hybrid/onsite) = eligible
c) Management positions ONLY (discard technical hands-on)
d) Set status='disqualified' + score=0 for discarded jobs
   so only eligible jobs remain for AI scoring.
"""
import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL", "postgresql://job_matcher:JobMatcher2024!@db:5432/job_matcher")

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
    'leadership', 'lead ', ' lead', 'team lead',
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
    'analyst', 'technician', 'specialist',
]

# BRAZIL KEYWORDS
BRAZIL_KEYWORDS = ['brazil', 'brasil', 'são paulo', 'sao paulo', 'rio de janeiro',
                   'brasília', 'brasilia', 'belo horizonte', 'curitiba', 'porto alegre',
                   'salvador', 'recife', 'fortaleza', 'campinas', 'br-', ', br',
                   'latin america', 'latam']

# REMOTE KEYWORDS
REMOTE_KEYWORDS = ['remote', 'anywhere', 'worldwide', 'work from home', 'wfh',
                   'telecommute', 'distributed']


def is_management_position(title):
    """Check if job title is management/leadership"""
    title_lower = str(title or '').lower()

    # Has management keyword = eligible
    if any(kw in title_lower for kw in MANAGEMENT_KEYWORDS):
        return True, 'management'

    # Has technical keyword without management = discard
    if any(kw in title_lower for kw in TECHNICAL_HANDS_ON):
        return False, 'technical_hands_on'

    # Default: could be relevant, keep for scoring
    return True, 'needs_scoring'


def is_location_eligible(location, job_title, job_description):
    """Check if job location is eligible (Brazil=all, International=remote only)"""
    location_lower = str(location or '').lower()
    title_lower = str(job_title or '').lower()
    desc_lower = str(job_description or '')[:2000].lower()

    # Brazil-based = ALL work types eligible
    for kw in BRAZIL_KEYWORDS:
        if kw in location_lower:
            return True, 'brazil_local'

    # International = check for remote
    for kw in REMOTE_KEYWORDS:
        if kw in location_lower or kw in title_lower:
            return True, 'international_remote'

    # Check description for explicit remote mentions
    if any(phrase in desc_lower for phrase in [
        'fully remote', '100% remote', 'work from anywhere',
        'remote position', 'remote role', 'remote-first',
        'location: remote', 'remote work',
    ]):
        return True, 'international_remote'

    return False, 'international_not_remote'


def classify_job(title, location, description):
    """Full classification of a job"""
    is_mgmt, mgmt_reason = is_management_position(title)
    if not is_mgmt:
        return False, f'discard_technical: {mgmt_reason}'

    is_loc_ok, loc_reason = is_location_eligible(location, title, description)
    if not is_loc_ok:
        return False, f'discard_location: {loc_reason}'

    return True, f'eligible: {loc_reason}'


def run():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get ALL jobs
    cur.execute("""
        SELECT id, job_id, job_title, location, job_description, score, status
        FROM jobs
        ORDER BY created_at DESC
    """)
    all_jobs = cur.fetchall()

    print(f"{'=' * 70}")
    print(f"  JOB CLASSIFICATION PRE-FILTER — {len(all_jobs)} jobs")
    print(f"{'=' * 70}")
    print(f"  Rules:")
    print(f"    ✓ Management/leadership titles ONLY")
    print(f"    ✓ Brazil = any work type | International = remote only")
    print(f"    ✗ Technical hands-on → score=0, status=disqualified")
    print(f"    ✗ International non-remote → score=0, status=disqualified")
    print(f"{'=' * 70}\n")

    stats = {
        'total': len(all_jobs),
        'eligible_management': 0,
        'eligible_needs_scoring': 0,
        'eligible_brazil': 0,
        'eligible_remote': 0,
        'discard_technical': 0,
        'discard_location': 0,
    }

    eligible_jobs = []
    discard_batch = []

    for row in all_jobs:
        job_id = row['id']
        title = row['job_title']
        location = row['location']
        description = row['job_description']

        is_eligible, reason = classify_job(title, location, description)

        if is_eligible:
            if 'brazil' in reason:
                stats['eligible_brazil'] += 1
            else:
                stats['eligible_remote'] += 1

            _, mgmt_reason = is_management_position(title)
            if mgmt_reason == 'management':
                stats['eligible_management'] += 1
            else:
                stats['eligible_needs_scoring'] += 1

            eligible_jobs.append((title, location, reason))
        else:
            if 'technical' in reason:
                stats['discard_technical'] += 1
                justification = 'Auto-filtered: Technical hands-on role — seeking management positions only'
            else:
                stats['discard_location'] += 1
                justification = 'Auto-filtered: International position not accepting remote candidates'

            discard_batch.append((justification, job_id))

    # Batch update discarded jobs
    if discard_batch:
        cur.executemany("""
            UPDATE jobs
            SET score = 0,
                status = 'skipped',
                justification = %s,
                updated_at = now()
            WHERE id = %s
        """, discard_batch)

    # Set eligible jobs to 'pending' status (ready for AI scoring)
    cur.execute("""
        UPDATE jobs
        SET status = 'pending'
        WHERE score IS NULL AND status != 'skipped'
    """)

    conn.commit()

    # ── Summary ──
    total_discard = stats['discard_technical'] + stats['discard_location']
    total_eligible = stats['total'] - total_discard

    print(f"  RESULTS:")
    print(f"  {'─' * 60}")
    print(f"  Total jobs analyzed:     {stats['total']:>6}")
    print(f"")
    print(f"  ✅ ELIGIBLE (ready for AI scoring):  {total_eligible:>6}")
    print(f"     ├─ Management titles:             {stats['eligible_management']:>6}")
    print(f"     ├─ Other/ambiguous titles:         {stats['eligible_needs_scoring']:>6}")
    print(f"     ├─ Brazil-based:                   {stats['eligible_brazil']:>6}")
    print(f"     └─ International remote:           {stats['eligible_remote']:>6}")
    print(f"")
    print(f"  ❌ DISQUALIFIED (score=0):            {total_discard:>6}")
    print(f"     ├─ Technical hands-on roles:       {stats['discard_technical']:>6}")
    print(f"     └─ International non-remote:       {stats['discard_location']:>6}")
    print(f"  {'─' * 60}")
    print(f"")
    print(f"  🎯 Reduction: {stats['total']} → {total_eligible} jobs"
          f" ({100 * total_discard / stats['total']:.1f}% filtered out)")

    # Show sample eligible
    print(f"\n  ── Sample ELIGIBLE jobs ──")
    for title, loc, reason in eligible_jobs[:15]:
        tag = '🇧🇷' if 'brazil' in reason else '🌍'
        print(f"    {tag} {str(title)[:50]:<52} {str(loc)[:30]}")

    # Show sample discarded
    print(f"\n  ── Sample DISCARDED jobs ──")
    cur.execute("""
        SELECT job_title, location, justification FROM jobs
        WHERE status = 'disqualified'
        ORDER BY random()
        LIMIT 10
    """)
    for row in cur.fetchall():
        tag = '🔧' if 'Technical' in (row[2] or '') else '📍'
        print(f"    {tag} {str(row[0])[:50]:<52} {str(row[1])[:30]}")

    cur.close()
    conn.close()

    print(f"\n  ✅ Done! Run AI scoring on the {total_eligible} eligible jobs.\n")
    return stats


if __name__ == "__main__":
    run()
