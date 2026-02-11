#!/usr/bin/env python3
"""
AI Job Matcher - Optimized Python Workflow
===========================================
100% Python-based job matching with PostgreSQL

Key Optimization: 1 AI call per job (instead of 18+)

Usage:
    python job_matcher.py                    # Process pending jobs
    python job_matcher.py --batch-size 50    # Process 50 jobs
    python job_matcher.py --dry-run          # Preview without AI calls
    
Requirements:
    pip install psycopg2-binary openai python-dotenv google-api-python-client
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    """Application configuration"""
    # Database
    db_host: str = os.getenv('DB_HOST', 'localhost')
    db_port: int = int(os.getenv('DB_PORT', '5432'))
    db_name: str = os.getenv('DB_NAME', 'job_matcher')
    db_user: str = os.getenv('DB_USER', 'job_matcher')
    db_password: str = os.getenv('DB_PASSWORD', 'JobMatcher2024!')
    
    # OpenAI
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Telegram Notifications
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Processing
    batch_size: int = 50
    score_threshold: int = 75
    rate_limit_seconds: float = 0.5
    
    # Resume (Google Docs ID containing your resume)
    resume_doc_id: str = os.getenv('RESUME_DOC_ID', '1qdjwfXDlfKKOBR0v5qNVU0DtlD65eObakN5t2XTdgho')
    resume_folder_id: str = os.getenv('RESUME_FOLDER_ID', '1yicugNqc33obnrVA9juwk84-Am6bKPFQ')


@dataclass
class JobResult:
    """Result of AI job scoring"""
    job_id: int
    score: int
    qualified: bool
    justification: str
    key_matches: List[str]
    gaps: List[str]
    tokens_used: int
    processing_time_ms: int


# ============================================================
# DATABASE OPERATIONS
# ============================================================

class Database:
    """PostgreSQL database handler"""
    
    def __init__(self, config: Config):
        self.config = config
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = psycopg2.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            dbname=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password
        )
        logger.info(f"Connected to PostgreSQL at {self.config.db_host}:{self.config.db_port}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def fetch_pending_jobs(self, limit: int) -> List[Dict]:
        """Fetch pending jobs for processing"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE jobs 
                SET status = 'processing', updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM jobs 
                    WHERE status = 'pending' 
                    ORDER BY created_at 
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING *
            """, (limit,))
            jobs = cur.fetchall()
            self.conn.commit()
        
        logger.info(f"Fetched {len(jobs)} pending jobs for processing")
        return [dict(job) for job in jobs]
    
    def update_job_result(self, result: JobResult):
        """Update job with AI scoring results"""
        status = 'qualified' if result.qualified else 'low_score'
        
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE jobs SET
                    score = %s,
                    justification = %s,
                    status = %s,
                    tokens_used = %s,
                    scored_at = NOW(),
                    processed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (
                result.score,
                result.justification,
                status,
                result.tokens_used,
                result.job_id
            ))
            self.conn.commit()
    
    def update_resume_url(self, job_id: int, resume_url: str):
        """Update job with custom resume URL"""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE jobs SET
                    custom_resume_url = %s,
                    status = 'enhanced',
                    updated_at = NOW()
                WHERE id = %s
            """, (resume_url, job_id))
            self.conn.commit()
    
    def mark_error(self, job_id: int, error_message: str):
        """Mark job as errored"""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE jobs SET
                    status = 'error',
                    error_message = %s,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE id = %s
            """, (error_message[:500], job_id))
            self.conn.commit()
    
    def log_batch(self, batch_id: str, processed: int, qualified: int, tokens: int):
        """Log batch processing stats"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO processing_logs (batch_id, event_type, details)
                VALUES (%s, 'batch_completed', %s)
            """, (
                batch_id,
                json.dumps({
                    'processed_count': processed,
                    'qualified_count': qualified,
                    'total_tokens': tokens
                })
            ))
            self.conn.commit()
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'qualified') as qualified,
                    COUNT(*) FILTER (WHERE status = 'enhanced') as enhanced,
                    COUNT(*) FILTER (WHERE status = 'low_score') as rejected,
                    COUNT(*) FILTER (WHERE status = 'error') as errors,
                    COUNT(*) as total,
                    ROUND(AVG(score)::numeric, 1) as avg_score
                FROM jobs
            """)
            return dict(cur.fetchone())


# ============================================================
# TELEGRAM NOTIFICATIONS
# ============================================================

class TelegramNotifier:
    """Send notifications to Telegram when batches complete"""
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = bool(config.telegram_bot_token and config.telegram_chat_id)
        if self.enabled:
            logger.info("Telegram notifications enabled")
        else:
            logger.warning("Telegram notifications disabled (no token/chat_id)")
    
    def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message via Telegram Bot API"""
        if not self.enabled:
            return False
        
        try:
            import urllib.request
            import urllib.parse
            
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id': self.config.telegram_chat_id,
                'text': text,
                'parse_mode': parse_mode
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    def send_batch_summary(self, stats: Dict, elapsed: float, qualified_jobs: List[Dict] = None):
        """Send batch completion summary to Telegram"""
        processed = stats.get('processed', 0)
        qualified = stats.get('qualified', 0)
        rejected = processed - qualified - stats.get('errors', 0)
        errors = stats.get('errors', 0)
        tokens = stats.get('total_tokens', 0)
        
        # Calculate cost (gpt-4o-mini pricing)
        cost = (tokens / 1_000_000) * 0.15
        
        # Build message
        message = f"""🎯 <b>Job Matcher - Batch Complete</b>

📊 <b>Results:</b>
✅ Qualified: <b>{qualified}</b> jobs (≥75%)
❌ Rejected: <b>{rejected}</b> jobs
⚠️ Errors: {errors}

📈 <b>Stats:</b>
• Processed: {processed} jobs
• Time: {elapsed:.1f}s
• Tokens: {tokens:,}
• Cost: ${cost:.4f}"""

        # Add qualified job details if any
        if qualified_jobs and len(qualified_jobs) > 0:
            message += "\n\n🌟 <b>Qualified Positions:</b>"
            for job in qualified_jobs[:5]:  # Max 5 jobs in message
                company = job.get('company_name', 'Unknown')[:25]
                title = job.get('job_title', 'Unknown')[:30]
                score = job.get('score', 0)
                url = job.get('job_url', '')
                message += f"\n• {company} - {title} ({score}%)"
                if url:
                    message += f"\n  <a href='{url}'>View Job</a>"
            
            if len(qualified_jobs) > 5:
                message += f"\n... and {len(qualified_jobs) - 5} more"
        
        self._send_message(message)
        logger.info("Telegram batch summary sent")
    
    def send_qualified_job(self, job: Dict, score: int, justification: str, resume_url: str = None):
        """Send immediate notification for a qualified job with apply and CV links"""
        company = job.get('company_name', 'Unknown')
        title = job.get('job_title', 'Unknown')
        job_url = job.get('job_url', '')
        apply_url = job.get('apply_url', '') or job_url  # Fallback to job_url
        location = job.get('location', 'Not specified')
        work_type = job.get('work_type', '')
        
        # Build the message for mobile-friendly quick action
        message = f"""🎉 <b>New Qualified Match!</b>

🏢 <b>{company}</b>
💼 {title}
📍 {location}"""

        if work_type:
            message += f" | {work_type}"
        
        message += f"""

📊 Score: <b>{score}%</b>

📝 <i>{justification[:200]}</i>"""

        # Add prominent action buttons section
        message += "\n\n" + "="*30 + "\n📱 <b>QUICK ACTIONS</b>\n" + "="*30

        if apply_url:
            message += f"\n\n🚀 <a href='{apply_url}'><b>APPLY NOW</b></a>"
        
        if resume_url:
            message += f"\n\n📄 <a href='{resume_url}'><b>Your Enhanced CV</b></a>"
        
        if job_url and job_url != apply_url:
            message += f"\n\n🔗 <a href='{job_url}'>View Job Details</a>"
        
        self._send_message(message)


# ============================================================
# AI SCORER - SINGLE CALL PER JOB
# ============================================================

class AIScorer:
    """
    Optimized AI Job Scorer
    
    Uses a SINGLE OpenAI call per job (vs 18+ with n8n agents)
    Replicates the exact n8n workflow prompts in a single call.
    """
    
    # Manoel Benicio's Resume - Embedded for scoring
    CANDIDATE_RESUME = """📄 RESUME — MANOEL BENICIO

Manoel Benicio
📍 São Paulo, Brazil | 📧 manoel.benicio@icloud.com | 📞 +55 11 99364-4444 | 🌐 linkedin.com/in/manoel-benicio-filho

🎯 Profile
Technology Modernization & Digital Transformation leader with 20+ years delivering enterprise-scale modernization and legacy migration programs. Strong expertise in application modernization, cloud adoption, and emerging technology integration. Proven impact across complex environments, including customer revenue growth (25% to 50.5%), IT cost reduction (37.4%), and system performance improvement (65%). Certified multi-cloud architect with hands-on leadership across AWS, Azure, GCP, and OCI.

🧩 Core Competencies
- Digital Transformation Strategy
- Application Modernization & Legacy Migration
- Cloud Adoption & Technology Roadmaps
- Innovation Leadership & Emerging Technologies
- Technical Debt Reduction & Architecture Governance
- Business Case Development & Executive Communication
- Revenue Growth (25% to 50.5%) and Cost Optimization

💼 Experience

Head Strategic Business Development – Apps & Cloud Modernization
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Managed a diverse engineering team delivering projects across Americas and EMEA.
- Developed products and solutions that increased customer revenue from 25% to 50.5% over 2 years.
- Managed annual budget of $200M, driving a 37.4% reduction in IT expenditure.
- Led cloud modernization initiatives, migrating legacy systems to cloud platforms with improved efficiency.

Sr Data & Analytics Practice Manager
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Oversaw large-scale IT projects in the health services sector with timely execution.
- Led cross-functional teams of data engineers delivering data-driven strategies.
- Reduced project completion time by 25% through agile methodologies.
- Implemented data governance frameworks reducing data errors by 25%.

Head Cloud & Data Professional Services
Andela | New York, USA | 2022 – 2023
- Led developers, security, and infrastructure professionals for cloud and data programs.
- Facilitated successful legacy migrations and upgrades across cloud/data platforms.
- Built a culture of ownership, inclusiveness, accountability, and urgency.
- Delivered solutions aligned to well-architected frameworks.

Sr Cloud Operations Manager
Telefonica Tech | São Paulo, Brazil | 2021 – 2022
- Accelerated customers' cloud migration journeys and digital transformation programs.
- Reported directly to the COO, managing transformation initiatives end-to-end.
- Orchestrated cloud infrastructure projects with 30% cost decrease and 65% performance increase.
- Negotiated complex cross-stakeholder issues and drove alignment through consensus.

Head Contracts for Cloud Services
Telefonica Tech | São Paulo, Brazil | 2020 – 2021
- Led major B2B contracts for LATAM region at a global insurance client.
- Enabled the sales team to promote new products and solutions.
- Partnered with operations to migrate on-prem applications to public cloud platforms.
- Managed datacenter teams in Brazil and Miami, overseeing CAPEX/OPEX.

Program Manager – Public Safety
NICE | Dallas, USA | 2016 – 2020
- Led developers, security, and infrastructure professionals in public safety programs.
- Acted as main sponsor managing Business Partner contracts (SLAs, performance, training, delivery).
- Managed partners across US regions delivering professional services.
- Collaborated with engineering and product teams to design and deploy NICE solutions.

🎓 Education
- MBA – Solutions Architecture | FIAP | 2020
- Bachelor's – Computer Systems Networking and Telecommunications | 2017

🛠 Skills (Technical & Leadership)
- Cloud Platforms: AWS, Azure, GCP, OCI
- Modernization: Legacy migration, application modernization, technical debt reduction
- Governance: Architecture governance, roadmap development, data governance
- Delivery & Ops: Cloud operations, large-scale program leadership, cost optimization
- Business & Leadership: Budget ownership, executive communication, business case development

📚 Certifications
- AWS Solution Architect
- AWS Security Specialty
- Azure Solutions Architect
- Azure Cybersecurity Architect
- Azure Security Engineer
- Azure Database Administrator
- Azure Network Engineer
- Oracle Multi-Cloud Architect
- Google Associate Cloud

🚀 Career Goal
To lead enterprise technology modernization initiatives that unlock innovation, reduce technical debt, and position organizations for sustainable competitive advantage."""
    
    # Scoring prompt - replicates the n8n "Expert LinkedIn job filtering agent" prompt
    # Enhanced with section-by-section evaluation
    SCORING_PROMPT = """You are an expert LinkedIn job posting filtering agent. 
Your only task is to determine whether or not the job posting provided to you is suitable for the specific candidate with the provided original resume.

The original resume may include various skills or qualifications. You will have to THINK DEEPLY and determine if any of the candidate's skillsets or knowledge is suitable to the job posting.

## STEP 1: ANALYZE THE JOB POSTING
Here is the information from the job posting and company:

Company Name: {company_name}
Job Title: {job_title}
Job Posting Description:
{job_description}

## STEP 2: REVIEW THE CANDIDATE'S RESUME
Here is the candidate's original resume:
{resume_text}

## STEP 3: SECTION-BY-SECTION EVALUATION
Evaluate the candidate against the job requirements in these key areas:

1. **Technical Skills Match** - Does the candidate have the required technical skills, tools, platforms?
2. **Experience Level** - Does seniority/years of experience align with requirements?
3. **Industry Experience** - Has the candidate worked in similar industries or domains?
4. **Leadership & Management** - For leadership roles, does candidate have management experience?
5. **Certifications** - Does candidate have relevant certifications mentioned in job posting?
6. **Location/Remote** - Is the location compatible (remote, hybrid, relocation)?

## STEP 4: CALCULATE SCORE
Based on your section-by-section analysis:
- 0-25: NOT suitable - major gaps in most areas
- 26-50: Weak match - some skills but significant gaps
- 51-74: Partial match - meets some requirements but missing key qualifications
- 75-89: Good match - meets most requirements, minor gaps only
- 90-100: Excellent match - meets or exceeds all requirements

## OUTPUT FORMAT
Respond with ONLY valid JSON (no markdown, no backticks):
{{
  "score": <0-100>,
  "qualified": <true if score >= 75, else false>,
  "justification": "<2-3 sentence summary of why this score>",
  "section_scores": {{
    "technical_skills": <0-100>,
    "experience_level": <0-100>,
    "industry_match": <0-100>,
    "leadership": <0-100>,
    "certifications": <0-100>
  }},
  "key_matches": ["<skill/experience that matches>", "..."],
  "gaps": ["<missing requirement>", "..."]
}}"""

    # Resume enhancement prompt - replicates the n8n "Expert resume building specialist" prompt
    # Enhanced to fill gaps identified in scoring phase
    RESUME_PROMPT = """You are an expert resume building specialist. 
Your task is to THINK DEEPLY to build AND enhance the originally provided resume based on the job requirements from the LinkedIn job postings.

NOTE:
The original resume may be unstructured but contains all of the candidate's relevant skills, experience and education.

## JOB POSTING DETAILS
Company Name: {company_name}
Job Title: {job_title}
Job Description:
{job_description}

## GAPS IDENTIFIED (from scoring phase)
These are the gaps between the candidate and job requirements that YOU MUST ADDRESS:
{gaps}

## CANDIDATE'S ORIGINAL RESUME
{resume_text}

## YOUR TASK: FILL THE GAPS
1. Review the GAPS listed above
2. For EACH gap, find related experience or knowledge from the candidate's background that can cover it
3. If the candidate doesn't have exact match, use TRANSFERABLE skills or related experience
4. Enhance bullet points to emphasize relevance to this specific job
5. Rewrite the Summary to directly address the job requirements

## INSTRUCTIONS
1. Take the original resume content and the job posting details
2. Recreate and enhance the resume to tailor and match the job requirements of the posting
3. Keep all original sections: Summary, Experience, Education, Skills, Certifications
4. Improve the content to highlight relevant skills and experiences
5. Maintain the professional structure and formatting
6. Output the COMPLETE enhanced resume with ALL sections
7. DO NOT include any "Complementary Skillsets" section

## IMPORTANT FORMATTING RULES
- Output ONLY clean HTML content, no markdown formatting
- Do NOT include ```html or ``` or backticks in your response
- Do NOT include the word "html" at the beginning
- Start your response directly with <h1> and end with the last section

## EXAMPLE STRUCTURE

<h1>Manoel Benicio</h1>
<div class="job-title"><strong>[Job Title tailored to position]</strong></div>

<div class="contact-section">
<strong>Contact:</strong>
<ul>
<li>Phone: +55 11 99364-4444</li>
<li>Email: manoel.benicio@icloud.com</li>
<li>Location: São Paulo, Brazil</li>
<li>LinkedIn: linkedin.com/in/manoel-benicio-filho</li>
</ul>
</div>

<h2><strong>Professional Summary</strong></h2>
<p class="summary">[Enhanced summary that directly addresses job requirements and shows candidate is perfect fit]</p>

<h2><strong>Professional Experience</strong></h2>
<div class="job-entry">
<h3>[Job Title]</h3>
<p class="company">[Company] | [Location] | [Dates]</p>
<ul>
<li>[Achievement bullet enhanced to match job requirements]</li>
<li>[Another achievement with metrics]</li>
</ul>
</div>

<h2><strong>Education</strong></h2>
[Education entries]

<h2><strong>Technical Skills</strong></h2>
[Skills organized by category, highlighting those relevant to job]

<h2><strong>Certifications</strong></h2>
[Relevant certifications]

Start your response directly with <h1> and end with the last section. No extra text or formatting markers."""

    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        # Use embedded resume by default
        self.resume_text = self.CANDIDATE_RESUME
        logger.info(f"Loaded embedded resume ({len(self.resume_text)} chars)")
    
    def load_resume(self, resume_text: str):
        """Load candidate resume for matching (overrides embedded resume)"""
        self.resume_text = resume_text
        logger.info(f"Loaded custom resume ({len(resume_text)} chars)")
    
    def score_job(self, job: Dict) -> JobResult:
        """
        Score a single job with ONE AI call
        
        This is the key optimization - replaces 18+ agent calls
        """
        start_time = time.time()
        
        prompt = self.SCORING_PROMPT.format(
            company_name=job.get('company_name', 'Unknown'),
            job_title=job.get('job_title', 'Unknown'),
            job_description=job.get('job_description', '')[:8000],  # Limit description
            resume_text=self.resume_text[:6000]  # Limit resume
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            # Parse JSON response
            result_data = json.loads(content)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return JobResult(
                job_id=job['id'],
                score=result_data.get('score', 0),
                qualified=result_data.get('qualified', False),
                justification=result_data.get('justification', ''),
                key_matches=result_data.get('key_matches', []),
                gaps=result_data.get('gaps', []),
                tokens_used=tokens_used,
                processing_time_ms=processing_time
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return JobResult(
                job_id=job['id'],
                score=0,
                qualified=False,
                justification=f"Parse error: {str(e)}",
                key_matches=[],
                gaps=[],
                tokens_used=0,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def generate_resume(self, job: Dict, gaps: List[str] = None) -> Optional[str]:
        """Generate customized resume HTML for qualified jobs
        
        Args:
            job: Job posting dict with company_name, job_title, job_description
            gaps: List of gaps identified in scoring phase to address
        """
        # Format gaps as bullet list for the prompt
        if gaps:
            gaps_text = "\n".join([f"- {gap}" for gap in gaps])
        else:
            gaps_text = "- No specific gaps identified - optimize for best match"
        
        prompt = self.RESUME_PROMPT.format(
            company_name=job.get('company_name', 'Unknown'),
            job_title=job.get('job_title', 'Unknown'),
            job_description=job.get('job_description', '')[:8000],
            resume_text=self.resume_text[:6000],
            gaps=gaps_text
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000
            )
            
            html_content = response.choices[0].message.content.strip()
            
            # Clean up any markdown artifacts
            html_content = html_content.replace('```html', '').replace('```', '').strip()
            
            # Wrap in full HTML document
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; line-height: 1.4; color: #333; font-size: 14px; }}
        h1 {{ font-size: 28px; margin-bottom: 8px; color: #000; }}
        h2 {{ font-size: 16px; margin-top: 20px; margin-bottom: 10px; color: #000; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        ul {{ list-style: disc; margin-left: 18px; margin-top: 0; }}
        li {{ margin-bottom: 5px; }}
        p {{ margin-bottom: 10px; text-align: justify; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
            
            return full_html
            
        except Exception as e:
            logger.error(f"Failed to generate resume: {e}")
            return None


# ============================================================
# GOOGLE DOCS INTEGRATION (Optional)
# ============================================================

class GoogleDocsClient:
    """Optional Google Docs integration for resume storage"""
    
    def __init__(self, credentials_file: str = 'credentials.json'):
        self.service = None
        self.drive_service = None
        self._init_services(credentials_file)
    
    def _init_services(self, credentials_file: str):
        """Initialize Google APIs"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            SCOPES = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = None
            token_file = 'token.json'
            
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(credentials_file):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                else:
                    logger.warning("No Google credentials found - resume upload disabled")
                    return
            
            self.service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("Google Docs API initialized")
            
        except ImportError:
            logger.warning("Google API libraries not installed - resume upload disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Google APIs: {e}")
    
    def get_resume_text(self, doc_id: str) -> str:
        """Fetch resume text from Google Docs"""
        if not self.service:
            return ""
        
        try:
            doc = self.service.documents().get(documentId=doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            text_parts = []
            for element in content:
                if 'paragraph' in element:
                    for elem in element['paragraph'].get('elements', []):
                        if 'textRun' in elem:
                            text_parts.append(elem['textRun'].get('content', ''))
            
            return ''.join(text_parts)
        except Exception as e:
            logger.error(f"Failed to fetch resume: {e}")
            return ""
    
    def upload_resume(self, html_content: str, title: str, folder_id: str) -> Optional[str]:
        """Upload HTML resume to Google Drive and return URL"""
        if not self.drive_service:
            return None
        
        try:
            # Create file
            file_metadata = {
                'name': title,
                'parents': [folder_id],
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            from googleapiclient.http import MediaInMemoryUpload
            media = MediaInMemoryUpload(
                html_content.encode('utf-8'),
                mimetype='text/html',
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Failed to upload resume: {e}")
            return None


# ============================================================
# MAIN PROCESSOR
# ============================================================

class JobMatcher:
    """Main job matching orchestrator"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config)
        self.db.connect()  # Establish database connection
        self.scorer = AIScorer(config)
        self.telegram = TelegramNotifier(config)
        self.docs = None
        
        # Track qualified jobs for notifications
        self.qualified_jobs = []
        
        # Stats tracking
        self.stats = {
            'processed': 0,
            'qualified': 0,
            'enhanced': 0,
            'errors': 0,
            'total_tokens': 0,
            'start_time': None
        }
    
    def setup(self):
        """Initialize all connections"""
        logger.info("=" * 60)
        logger.info("AI Job Matcher - Optimized Python Workflow")
        logger.info("=" * 60)
        
        # Database
        self.db.connect()
        
        # Google Docs (optional)
        try:
            self.docs = GoogleDocsClient()
            if self.docs.service:
                resume_text = self.docs.get_resume_text(self.config.resume_doc_id)
                if resume_text:
                    self.scorer.load_resume(resume_text)
                else:
                    logger.warning("Could not load resume from Google Docs")
        except Exception as e:
            logger.warning(f"Google Docs not available: {e}")
            self.docs = None
    
    def load_resume_from_file(self, file_path: str):
        """Load resume from local file as fallback"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                self.scorer.load_resume(f.read())
    
    def process_batch(self, dry_run: bool = False) -> Dict:
        """Process a batch of pending jobs"""
        self.stats['start_time'] = time.time()
        batch_id = f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Fetch pending jobs
        jobs = self.db.fetch_pending_jobs(self.config.batch_size)
        
        if not jobs:
            logger.info("No pending jobs to process")
            return self.stats
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing batch: {batch_id}")
        logger.info(f"Jobs to process: {len(jobs)}")
        logger.info(f"{'='*60}\n")
        
        for i, job in enumerate(jobs, 1):
            job_id = job['id']
            company = job.get('company_name', 'Unknown')[:30]
            title = job.get('job_title', 'Unknown')[:40]
            
            logger.info(f"[{i}/{len(jobs)}] {company} - {title}")
            
            if dry_run:
                logger.info("  → [DRY RUN] Would score this job")
                continue
            
            try:
                # Score job with SINGLE AI call
                result = self.scorer.score_job(job)
                
                # Update database
                self.db.update_job_result(result)
                
                # Track stats
                self.stats['processed'] += 1
                self.stats['total_tokens'] += result.tokens_used
                
                status_icon = "✓" if result.qualified else "✗"
                logger.info(f"  → {status_icon} Score: {result.score}% | {result.justification[:60]}...")
                
                if result.qualified:
                    self.stats['qualified'] += 1
                    
                    # Track qualified job for batch summary
                    job['score'] = result.score
                    self.qualified_jobs.append(job)
                    
                    # Generate custom resume for qualified jobs
                    resume_url = None
                    if self.docs and self.docs.service:
                        logger.info("  → Generating custom resume (filling gaps)...")
                        resume_html = self.scorer.generate_resume(job, gaps=result.gaps)
                        
                        if resume_html:
                            resume_title = f"{company} - {title} Resume"
                            resume_url = self.docs.upload_resume(
                                resume_html, 
                                resume_title, 
                                self.config.resume_folder_id
                            )
                            
                            if resume_url:
                                self.db.update_resume_url(job_id, resume_url)
                                self.stats['enhanced'] += 1
                                logger.info(f"  → Resume uploaded: {resume_url[:50]}...")
                    
                    # Send Telegram notification for qualified job with links
                    self.telegram.send_qualified_job(
                        job, 
                        result.score, 
                        result.justification,
                        resume_url
                    )
                
                # Rate limiting
                time.sleep(self.config.rate_limit_seconds)
                
            except Exception as e:
                logger.error(f"  → Error: {e}")
                self.db.mark_error(job_id, str(e))
                self.stats['errors'] += 1
        
        # Log batch completion
        elapsed = time.time() - self.stats['start_time']
        if not dry_run:
            self.db.log_batch(
                batch_id,
                self.stats['processed'],
                self.stats['qualified'],
                self.stats['total_tokens']
            )
            
            # Send Telegram notification
            self.telegram.send_batch_summary(
                self.stats, 
                elapsed, 
                self.qualified_jobs
            )
        
        # Print summary
        self._print_summary(elapsed)
        
        return self.stats
    
    def _print_summary(self, elapsed: float):
        """Print processing summary"""
        logger.info(f"\n{'='*60}")
        logger.info("BATCH COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Processed:    {self.stats['processed']} jobs")
        logger.info(f"Qualified:    {self.stats['qualified']} jobs (>= {self.config.score_threshold}%)")
        logger.info(f"Enhanced:     {self.stats['enhanced']} resumes generated")
        logger.info(f"Errors:       {self.stats['errors']} jobs")
        logger.info(f"Total Tokens: {self.stats['total_tokens']:,}")
        logger.info(f"Time:         {elapsed:.1f}s")
        
        if self.stats['processed'] > 0:
            avg_tokens = self.stats['total_tokens'] / self.stats['processed']
            logger.info(f"Avg Tokens:   {avg_tokens:.0f} per job")
            
            # Cost estimate (gpt-4o-mini pricing)
            cost = (self.stats['total_tokens'] / 1_000_000) * 0.15
            logger.info(f"Est. Cost:    ${cost:.4f}")
        
        logger.info(f"{'='*60}\n")
    
    def show_stats(self):
        """Display current database statistics"""
        stats = self.db.get_stats()
        
        logger.info("\n" + "="*60)
        logger.info("DATABASE STATISTICS")
        logger.info("="*60)
        logger.info(f"Total Jobs:   {stats['total']}")
        logger.info(f"Pending:      {stats['pending']}")
        logger.info(f"Processing:   {stats['processing']}")
        logger.info(f"Qualified:    {stats['qualified']}")
        logger.info(f"Enhanced:     {stats['enhanced']}")
        logger.info(f"Rejected:     {stats['rejected']}")
        logger.info(f"Errors:       {stats['errors']}")
        logger.info(f"Avg Score:    {stats['avg_score']}%")
        logger.info("="*60 + "\n")
    
    def cleanup(self):
        """Close all connections"""
        self.db.close()


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='AI Job Matcher - Optimized Python Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python job_matcher.py                      # Process pending jobs
    python job_matcher.py --batch-size 100     # Process 100 jobs
    python job_matcher.py --dry-run            # Preview without AI calls
    python job_matcher.py --stats              # Show database stats only
    python job_matcher.py --resume resume.txt  # Use local resume file
        """
    )
    
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of jobs to process (default: 50)')
    parser.add_argument('--threshold', type=int, default=75,
                       help='Qualification threshold (default: 75)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without making AI calls')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics only')
    parser.add_argument('--resume', type=str,
                       help='Path to local resume file (fallback)')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                       help='OpenAI model to use (default: gpt-4o-mini)')
    
    args = parser.parse_args()
    
    # Create config
    config = Config(
        batch_size=args.batch_size,
        score_threshold=args.threshold,
        openai_model=args.model
    )
    
    # Validate OpenAI key
    if not config.openai_api_key and not args.dry_run and not args.stats:
        logger.error("OPENAI_API_KEY environment variable not set!")
        logger.error("Set it with: export OPENAI_API_KEY=your-key-here")
        sys.exit(1)
    
    # Run processor
    matcher = JobMatcher(config)
    
    try:
        matcher.setup()
        
        # Load local resume if provided
        if args.resume:
            matcher.load_resume_from_file(args.resume)
        
        if args.stats:
            matcher.show_stats()
        else:
            matcher.process_batch(dry_run=args.dry_run)
            matcher.show_stats()
            
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        matcher.cleanup()


if __name__ == '__main__':
    main()
