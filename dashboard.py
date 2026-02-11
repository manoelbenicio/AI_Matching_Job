"""
AI Job Matcher - Enhanced Live Monitoring Dashboard
====================================================

Real-time Streamlit dashboard with:
- Live job processing metrics
- CV enhancement for qualified jobs
- CSV upload for importing jobs
- Full job browser with search/filter

Run with: streamlit run dashboard.py
Access at: http://localhost:8501
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import json
import csv
import io
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# Load environment variables
load_dotenv()

# Page configuration - Enterprise Style
st.set_page_config(
    page_title="AI Job Matcher | Enterprise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS - Enterprise Corporate Style
st.markdown("""
<style>
    /* Import professional enterprise fonts */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Enterprise Styling */
    .stApp {
        font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #f8f9fa;
    }
    
    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Enterprise Header Bar */
    .enterprise-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: white;
        padding: 12px 24px;
        margin: -1rem -1rem 1.5rem -1rem;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 0.5px;
        border-bottom: 3px solid #3182ce;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .enterprise-header .title {
        font-size: 20px;
        font-weight: 600;
    }
    
    .enterprise-header .subtitle {
        font-size: 12px;
        opacity: 0.85;
        font-weight: 400;
    }
    
    /* Section Headers */
    .section-header {
        background: #f1f5f9;
        border-left: 4px solid #1e3a5f;
        padding: 10px 16px;
        margin: 20px 0 15px 0;
        font-size: 14px;
        font-weight: 600;
        color: #1e3a5f;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Filter Bar */
    .filter-bar {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .filter-label {
        font-size: 11px;
        font-weight: 600;
        color: #1e3a5f;
        text-transform: uppercase;
        margin-bottom: 4px;
        letter-spacing: 0.3px;
    }
    
    /* Data Table Styling */
    .data-table {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .table-header {
        background: #f8fafc;
        border-bottom: 2px solid #e2e8f0;
        padding: 12px 16px;
        font-size: 11px;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .table-row {
        border-bottom: 1px solid #f1f5f9;
        padding: 14px 16px;
        font-size: 13px;
        color: #334155;
        transition: background 0.15s ease;
    }
    
    .table-row:hover {
        background: #f8fafc;
    }
    
    /* Results Counter */
    .results-count {
        font-size: 14px;
        font-weight: 600;
        color: #1e3a5f;
        padding: 12px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 0;
    }
    
    /* Status Badges - Enterprise Style */
    .status-qualified {
        background: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .status-rejected {
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .status-pending {
        background: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* Score Display */
    .score-high {
        color: #166534;
        font-weight: 700;
        font-size: 14px;
    }
    
    .score-low {
        color: #991b1b;
        font-weight: 600;
        font-size: 14px;
    }
    
    /* Action Buttons - Enterprise Style */
    .btn-primary {
        background: #1e3a5f;
        color: white;
        border: none;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 3px;
        cursor: pointer;
        transition: background 0.15s ease;
    }
    
    .btn-primary:hover {
        background: #2c5282;
    }
    
    .btn-outline {
        background: white;
        color: #1e3a5f;
        border: 1px solid #1e3a5f;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 3px;
        cursor: pointer;
    }
    
    /* Metrics Cards - Corporate Style */
    .metric-card-enterprise {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 4px;
    }
    
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Pagination */
    .pagination {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
        padding: 12px 16px;
        background: #f8fafc;
        border-top: 1px solid #e2e8f0;
        font-size: 12px;
        color: #64748b;
    }
    
    .page-btn {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 6px 12px;
        font-size: 12px;
        border-radius: 3px;
        cursor: pointer;
    }
    
    .page-btn.active {
        background: #1e3a5f;
        color: white;
        border-color: #1e3a5f;
    }
    
    /* Live Indicator */
    .live-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
        animation: pulse 2s infinite;
        margin-right: 6px;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* Streamlit widget overrides for enterprise look */
    .stSelectbox > div > div {
        font-size: 13px;
        border-radius: 3px;
    }
    
    .stTextInput > div > div > input {
        font-size: 13px;
        border-radius: 3px;
    }
    
    .stButton > button {
        font-size: 12px;
        font-weight: 600;
        border-radius: 3px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: #1e3a5f;
        color: white;
        border: none;
        font-size: 12px;
        font-weight: 600;
    }
    
    .stDownloadButton > button:hover {
        background: #2c5282;
        color: white;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 13px;
        font-weight: 600;
        color: #1e3a5f;
    }
    
    /* Sidebar enterprise styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: #1e3a5f;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label {
        color: white !important;
        font-size: 13px;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.15) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.25) !important;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Job row styling */
    .job-row {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        transition: border-color 0.15s ease;
    }
    
    .job-row:hover {
        border-color: #3182ce;
    }
    
    .company-name {
        font-weight: 600;
        color: #1e3a5f;
        font-size: 13px;
    }
    
    .job-title {
        color: #475569;
        font-size: 13px;
    }
    
    .job-meta {
        font-size: 11px;
        color: #94a3b8;
    }
    
    /* Badge styles */
    .badge-remote {
        background: #dbeafe;
        color: #1e40af;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-easy-apply {
        background: #dcfce7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# EMBEDDED RESUME (for CV Enhancement)
# ============================================================
EMBEDDED_RESUME = """Manoel Benicio
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
To lead enterprise technology modernization initiatives that unlock innovation, reduce technical debt, and position organizations for sustainable competitive advantage.
"""


class DatabaseConnection:
    """Manage database connection"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'job_matcher'),
                user=os.getenv('DB_USER', 'job_matcher'),
                password=os.getenv('DB_PASSWORD', 'JobMatcher2024!')
            )
            return True
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return False
    
    def get_stats(self):
        """Get overall statistics"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'qualified' THEN 1 END) as scored,
                        COUNT(CASE WHEN status = 'low_score' THEN 1 END) as low_score,
                        COUNT(CASE WHEN status = 'error' THEN 1 END) as errors,
                        COUNT(CASE WHEN score >= 70 THEN 1 END) as qualified,
                        AVG(score) FILTER (WHERE score IS NOT NULL) as avg_score,
                        COALESCE(SUM(tokens_used), 0) as total_tokens
                    FROM jobs
                """)
                row = cur.fetchone()
                return {
                    'total': row[0] or 0,
                    'pending': row[1] or 0,
                    'scored': row[2] or 0,
                    'low_score': row[3] or 0,
                    'errors': row[4] or 0,
                    'qualified': row[5] or 0,
                    'avg_score': round(row[6] or 0, 1),
                    'total_tokens': row[7] or 0
                }
        except Exception as e:
            st.error(f"Error fetching stats: {e}")
            return None
    
    def get_recent_jobs(self, limit=20):
        """Get recently processed jobs"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        company_name,
                        job_title,
                        score,
                        status,
                        justification,
                        custom_resume_url,
                        scored_at,
                        created_at
                    FROM jobs
                    WHERE status != 'pending'
                    ORDER BY scored_at DESC NULLS LAST, created_at DESC
                    LIMIT %s
                """, (limit,))
                
                columns = ['id', 'company', 'title', 'score', 'status', 
                          'justification', 'resume_url', 'scored_at', 'created_at']
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching jobs: {e}")
            return pd.DataFrame()
    
    def get_qualified_jobs(self, limit=50):
        """Get qualified jobs (score >= 70)"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        company_name,
                        job_title,
                        score,
                        justification,
                        custom_resume_url,
                        job_url,
                        apply_url,
                        job_description,
                        scored_at
                    FROM jobs
                    WHERE score >= 70
                    ORDER BY score DESC, scored_at DESC
                    LIMIT %s
                """, (limit,))
                
                columns = ['id', 'company', 'title', 'score', 'justification', 
                          'resume_url', 'job_url', 'apply_url', 'description', 'scored_at']
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching qualified jobs: {e}")
            return pd.DataFrame()
    
    def get_all_jobs(self, filters=None, limit=100, offset=0):
        """Get all jobs with optional filters"""
        try:
            where_clauses = ["1=1"]
            params = []
            
            if filters:
                if filters.get('search'):
                    where_clauses.append("(job_title ILIKE %s OR company_name ILIKE %s OR job_description ILIKE %s)")
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term, search_term])
                
                if filters.get('status') and filters['status'] != 'All':
                    where_clauses.append("status = %s")
                    params.append(filters['status'].lower())
                
                if filters.get('work_type') and filters['work_type'] != 'All':
                    where_clauses.append("work_type ILIKE %s")
                    params.append(f"%{filters['work_type']}%")
                
                if filters.get('min_score'):
                    where_clauses.append("score >= %s")
                    params.append(filters['min_score'])
                
                if filters.get('has_easy_apply'):
                    where_clauses.append("apply_url IS NOT NULL AND apply_url != ''")
            
            order_by = "created_at DESC"
            if filters and filters.get('sort_by'):
                sort_map = {
                    'Most Recent': 'created_at DESC',
                    'Highest Score': 'score DESC NULLS LAST',
                    'Company': 'company_name ASC',
                    'Job Title': 'job_title ASC',
                    'Posted Date': 'posted_date DESC NULLS LAST'
                }
                order_by = sort_map.get(filters['sort_by'], 'created_at DESC')
            
            query = f"""
                SELECT 
                    id, job_id, job_title, company_name, location, 
                    work_type, employment_type, salary_info, score, status,
                    justification, job_url, apply_url, posted_date, created_at
                FROM jobs
                WHERE {' AND '.join(where_clauses)}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                columns = ['id', 'job_id', 'title', 'company', 'location',
                          'work_type', 'employment_type', 'salary', 'score', 'status',
                          'justification', 'job_url', 'apply_url', 'posted_date', 'created_at']
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching jobs: {e}")
            return pd.DataFrame()
    
    def get_jobs_count(self, filters=None):
        """Get total count of jobs matching filters"""
        try:
            where_clauses = ["1=1"]
            params = []
            
            if filters:
                if filters.get('search'):
                    where_clauses.append("(job_title ILIKE %s OR company_name ILIKE %s OR job_description ILIKE %s)")
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term, search_term])
                
                if filters.get('status') and filters['status'] != 'All':
                    where_clauses.append("status = %s")
                    params.append(filters['status'].lower())
                
                if filters.get('work_type') and filters['work_type'] != 'All':
                    where_clauses.append("work_type ILIKE %s")
                    params.append(f"%{filters['work_type']}%")
                
                if filters.get('min_score'):
                    where_clauses.append("score >= %s")
                    params.append(filters['min_score'])
            
            query = f"SELECT COUNT(*) FROM jobs WHERE {' AND '.join(where_clauses)}"
            
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()[0]
        except Exception as e:
            return 0
    
    def get_job_by_id(self, job_id):
        """Get single job by ID"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
                return dict(cur.fetchone()) if cur.rowcount > 0 else None
        except Exception as e:
            return None
    
    def update_job_resume(self, job_id, resume_url):
        """Update job with enhanced resume URL"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET custom_resume_url = %s, updated_at = NOW() WHERE id = %s",
                    (resume_url, job_id)
                )
                self.conn.commit()
                return True
        except Exception as e:
            return False
    
    def import_jobs_from_csv(self, csv_data):
        """Import jobs from CSV data"""
        try:
            reader = csv.DictReader(io.StringIO(csv_data))
            imported = 0
            skipped = 0
            
            with self.conn.cursor() as cur:
                for row in reader:
                    # Map CSV columns to database columns
                    job_id = row.get('job_id', row.get('id', f"csv-{imported}-{datetime.now().timestamp()}"))
                    
                    # Check if job already exists
                    cur.execute("SELECT id FROM jobs WHERE job_id = %s", (job_id,))
                    if cur.fetchone():
                        skipped += 1
                        continue
                    
                    cur.execute("""
                        INSERT INTO jobs (
                            job_id, job_title, company_name, job_description, 
                            location, salary_info, seniority_level, employment_type,
                            work_type, job_url, apply_url, time_posted, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                    """, (
                        job_id,
                        row.get('job_title', row.get('title', '')),
                        row.get('company_name', row.get('company', '')),
                        row.get('job_description', row.get('description', '')),
                        row.get('location', ''),
                        row.get('salary_info', row.get('salary', '')),
                        row.get('seniority_level', row.get('seniority', '')),
                        row.get('employment_type', ''),
                        row.get('work_type', row.get('remote', '')),
                        row.get('job_url', row.get('url', '')),
                        row.get('apply_url', ''),
                        row.get('time_posted', row.get('posted', ''))
                    ))
                    imported += 1
                
                self.conn.commit()
                return imported, skipped
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def get_score_distribution(self):
        """Get score distribution for chart"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN score >= 90 THEN '90-100 (Excellent)'
                            WHEN score >= 80 THEN '80-89 (Great)'
                            WHEN score >= 70 THEN '70-79 (Good)'
                            WHEN score >= 50 THEN '50-69 (Partial)'
                            WHEN score >= 25 THEN '25-49 (Weak)'
                            ELSE '0-24 (No Match)'
                        END as score_range,
                        COUNT(*) as count
                    FROM jobs
                    WHERE score IS NOT NULL
                    GROUP BY 
                        CASE 
                            WHEN score >= 90 THEN '90-100 (Excellent)'
                            WHEN score >= 80 THEN '80-89 (Great)'
                            WHEN score >= 70 THEN '70-79 (Good)'
                            WHEN score >= 50 THEN '50-69 (Partial)'
                            WHEN score >= 25 THEN '25-49 (Weak)'
                            ELSE '0-24 (No Match)'
                        END
                    ORDER BY MIN(score) DESC
                """)
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=['range', 'count']) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    def get_processing_timeline(self):
        """Get processing timeline for chart"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        DATE(scored_at) as date,
                        COUNT(*) as processed,
                        COUNT(CASE WHEN score >= 70 THEN 1 END) as qualified
                    FROM jobs
                    WHERE scored_at IS NOT NULL
                    GROUP BY DATE(scored_at)
                    ORDER BY date DESC
                    LIMIT 14
                """)
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=['date', 'processed', 'qualified']) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    def get_top_companies(self, limit=10):
        """Get top companies with most qualified jobs"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        company_name,
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN score >= 70 THEN 1 END) as qualified,
                        ROUND(AVG(score)::numeric, 1) as avg_score
                    FROM jobs
                    WHERE score IS NOT NULL
                    GROUP BY company_name
                    HAVING COUNT(CASE WHEN score >= 70 THEN 1 END) > 0
                    ORDER BY qualified DESC, avg_score DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=['company', 'total', 'qualified', 'avg_score']) if rows else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()


def generate_enhanced_cv(job_description, job_title, company_name):
    """Generate enhanced CV tailored to the job"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""You are an expert resume writer. Enhance the following resume to better match this specific job opportunity.

JOB DETAILS:
- Company: {company_name}
- Position: {job_title}
- Description: {job_description[:3000]}

ORIGINAL RESUME:
{EMBEDDED_RESUME}

INSTRUCTIONS:
1. Rewrite the Professional Summary to directly address this role's requirements
2. Reorder and emphasize bullet points that match the job requirements
3. Add relevant keywords from the job description naturally
4. Highlight transferable skills that match the role
5. Keep the same structure but optimize content for ATS systems
6. Make it compelling for human reviewers

OUTPUT FORMAT:
Return ONLY the enhanced resume in clean markdown format, ready to copy/paste.
Do not include explanations or commentary."""

        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating CV: {str(e)}"


def render_header():
    """Render enterprise dashboard header"""
    st.markdown('''
        <div class="enterprise-header">
            <div>
                <div class="title">AI JOB MATCHER</div>
                <div class="subtitle">Enterprise Career Intelligence Platform</div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="font-size: 12px;"><span class="live-indicator"></span> Live</span>
                <span style="font-size: 12px; opacity: 0.8;">''' + datetime.now().strftime("%d %b %Y %H:%M") + '''</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)


def render_metrics(stats):
    """Render main metrics"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="📊 Total Jobs", value=stats['total'])
    
    with col2:
        st.metric(label="⏳ Pending", value=stats['pending'])
    
    with col3:
        st.metric(
            label="✅ Qualified",
            value=stats['qualified'],
            delta=f"{round(stats['qualified']/stats['total']*100, 1)}%" if stats['total'] > 0 else "0%"
        )
    
    with col4:
        st.metric(label="📈 Avg Score", value=f"{stats['avg_score']}%")
    
    with col5:
        cost = (stats['total_tokens'] / 1_000_000) * 0.15
        st.metric(label="💰 Est. Cost", value=f"${cost:.2f}")


def render_progress_bar(stats):
    """Render processing progress"""
    if stats['total'] > 0:
        processed = stats['scored'] + stats['low_score'] + stats['errors']
        progress = processed / stats['total']
        st.markdown("### Processing Progress")
        st.progress(progress)
        st.caption(f"Processed {processed} of {stats['total']} jobs ({progress*100:.1f}%)")


def render_charts(db):
    """Render analytics charts"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Score Distribution")
        dist_df = db.get_score_distribution()
        if not dist_df.empty:
            colors = ['#10B981', '#34D399', '#6EE7B7', '#FCD34D', '#F87171', '#EF4444']
            fig = px.pie(dist_df, values='count', names='range', color_discrete_sequence=colors)
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No scored jobs yet")
    
    with col2:
        st.markdown("### 📈 Processing Timeline")
        timeline_df = db.get_processing_timeline()
        if not timeline_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=timeline_df['date'], y=timeline_df['processed'], name='Processed', marker_color='#667eea'))
            fig.add_trace(go.Bar(x=timeline_df['date'], y=timeline_df['qualified'], name='Qualified', marker_color='#10B981'))
            fig.update_layout(height=300, barmode='overlay', margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No processing data yet")


def render_recent_activity(db):
    """Render recent activity feed"""
    st.markdown("### 📝 Recent Activity")
    recent_df = db.get_recent_jobs(15)
    
    if recent_df.empty:
        st.info("No processed jobs yet. Run `python job_matcher.py` to start processing!")
        return
    
    for _, row in recent_df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                company = row['company'] or 'Unknown'
                title = row['title'] or 'Unknown'
                st.markdown(f"**{company[:25]}** - {title[:40]}")
            
            with col2:
                score = row['score']
                if score is not None and score >= 70:
                    st.markdown(f'<span class="qualified-badge">✅ {score}%</span>', unsafe_allow_html=True)
                elif score is not None:
                    st.markdown(f'<span class="rejected-badge">❌ {score}%</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="pending-badge">{row["status"]}</span>', unsafe_allow_html=True)
            
            with col3:
                if row['resume_url']:
                    st.markdown(f"[📄 Resume]({row['resume_url']})")
            
            st.divider()


def render_qualified_jobs(db):
    """Render qualified jobs with CV enhancement and export functionality"""
    st.markdown("### 🌟 Qualified Positions (Score ≥ 70%)")
    
    qualified_df = db.get_qualified_jobs(100)  # Get more jobs for export
    
    if qualified_df.empty:
        st.info("No qualified jobs found yet.")
        return
    
    # Initialize session state for selections
    if 'selected_jobs' not in st.session_state:
        st.session_state.selected_jobs = set()
    
    # Export Header Bar
    st.markdown("""
    <div class="filter-bar">
        <strong>📤 Export Selected Jobs</strong>
    </div>
    """, unsafe_allow_html=True)
    
    col_select, col_count, col_csv, col_excel = st.columns([2, 1, 1, 1])
    
    with col_select:
        select_all = st.checkbox(
            "☑️ Select All Jobs", 
            key="select_all_qualified",
            help="Select all jobs for export"
        )
    
    with col_count:
        selected_count = len(st.session_state.selected_jobs)
        st.markdown(f"**{selected_count}** selected")
    
    # Handle select all
    if select_all:
        st.session_state.selected_jobs = set(qualified_df['id'].tolist())
    
    # Export buttons
    with col_csv:
        if st.button("📥 Export CSV", use_container_width=True, disabled=selected_count == 0):
            export_df = qualified_df[qualified_df['id'].isin(st.session_state.selected_jobs)]
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"qualified_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv_qualified"
            )
    
    with col_excel:
        if st.button("📊 Export Excel", use_container_width=True, disabled=selected_count == 0):
            import io
            export_df = qualified_df[qualified_df['id'].isin(st.session_state.selected_jobs)]
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Qualified Jobs')
            excel_data = buffer.getvalue()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_data,
                file_name=f"qualified_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_qualified"
            )
    
    st.divider()
    st.markdown(f"**{len(qualified_df)}** qualified jobs found")
    
    # Render each job with checkbox
    for idx, row in qualified_df.iterrows():
        col_check, col_job = st.columns([0.05, 0.95])
        
        with col_check:
            is_selected = st.checkbox(
                "", 
                value=row['id'] in st.session_state.selected_jobs,
                key=f"check_{row['id']}",
                label_visibility="collapsed"
            )
            if is_selected:
                st.session_state.selected_jobs.add(row['id'])
            elif row['id'] in st.session_state.selected_jobs:
                st.session_state.selected_jobs.discard(row['id'])
        
        with col_job:
            with st.expander(f"**{row['company']}** - {row['title']} ({row['score']}%)"):
                st.write("**AI Justification:**")
                st.write(row['justification'] or "No justification available")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if row['job_url']:
                        st.link_button("🔗 View Job", row['job_url'])
                with col2:
                    if row['apply_url']:
                        st.link_button("📝 Apply Now", row['apply_url'])
                    elif row['job_url']:
                        st.link_button("📝 Apply", row['job_url'])
                with col3:
                    if row['resume_url']:
                        st.link_button("📄 View CV", row['resume_url'])
                
                st.divider()
                
                # CV Enhancement Button - Premium PDF
                col_cv1, col_cv2 = st.columns(2)
                with col_cv1:
                    if st.button(f"📄 Generate Premium PDF CV", key=f"cv_{row['id']}"):
                        with st.spinner("🚀 Creating Fortune 500 quality CV... (15-30 seconds)"):
                            try:
                                from premium_cv_generator import PremiumCVGenerator
                                gemini_key = st.session_state.get('gemini_api_key', '')
                                generator = PremiumCVGenerator(gemini_api_key=gemini_key)
                                
                                job_data = {
                                    'company_name': row['company'],
                                    'job_title': row['title'],
                                    'job_description': row['description'] or ''
                                }
                                
                                result = generator.generate_tailored_cv(EMBEDDED_RESUME, job_data)
                                
                                if result['pdf_generated'] and result['pdf_path']:
                                    st.success("✅ Premium PDF CV Generated!")
                                    
                                    # Read PDF for download
                                    with open(result['pdf_path'], 'rb') as pdf_file:
                                        pdf_data = pdf_file.read()
                                    
                                    st.download_button(
                                        label="📥 Download PDF Resume",
                                        data=pdf_data,
                                        file_name=f"Resume_{row['company']}_{row['title'][:20]}.pdf",
                                        mime="application/pdf",
                                        type="primary"
                                    )
                                    
                                    st.caption(f"📁 Also saved to: {result['pdf_path']}")
                                else:
                                    # Fallback to HTML
                                    st.warning("PDF generation unavailable, HTML version created")
                                    st.download_button(
                                        label="📥 Download HTML Resume",
                                        data=result['html'],
                                        file_name=f"Resume_{row['company']}_{row['title'][:20]}.html",
                                        mime="text/html"
                                    )
                            except Exception as e:
                                st.error(f"Error generating CV: {str(e)}")
                                # Fallback to old method
                                enhanced_cv = generate_enhanced_cv(
                                    row['description'] or '',
                                    row['title'],
                                    row['company']
                                )
                                st.markdown("### Tailored Resume (Text):")
                                st.markdown(enhanced_cv)


def render_manual_job_cv():
    """Render manual job CV generation page - with LinkedIn URL auto-fetch"""
    st.markdown("### 🔗 Manual Job CV Generator")
    st.markdown("""
    Generate a tailored CV for any job you find on LinkedIn or elsewhere.
    **Paste a LinkedIn URL to auto-fetch job details, or enter manually.**
    """)
    
    st.divider()
    
    # Initialize session state for fetched job data
    if 'fetched_job' not in st.session_state:
        st.session_state.fetched_job = {
            'company_name': '',
            'job_title': '',
            'location': '',
            'job_description': '',
            'job_url': ''
        }
    
    # URL input with Fetch button (OUTSIDE the form for instant action)
    st.markdown("#### 🔗 LinkedIn URL Auto-Fetch")
    col_url, col_fetch = st.columns([4, 1])
    
    with col_url:
        job_url = st.text_input(
            "Paste LinkedIn Job URL", 
            placeholder="https://www.linkedin.com/jobs/view/... or /jobs/search/?currentJobId=...",
            key="linkedin_url_input",
            label_visibility="collapsed"
        )
    
    with col_fetch:
        fetch_clicked = st.button("🔍 Fetch", use_container_width=True, type="primary")
    
    # Handle fetch click
    if fetch_clicked and job_url:
        with st.spinner("🔄 Fetching job details from LinkedIn..."):
            try:
                from linkedin_job_fetcher import LinkedInJobFetcher
                fetcher = LinkedInJobFetcher()
                
                if not fetcher.is_linkedin_url(job_url):
                    st.warning("⚠️ This doesn't look like a LinkedIn job URL")
                else:
                    result = fetcher.fetch_job_details(job_url)
                    
                    if result['success']:
                        st.success(f"✅ Found: **{result['job_title']}** at **{result['company_name']}**")
                        
                        # Store in session state
                        st.session_state.fetched_job = {
                            'company_name': result['company_name'],
                            'job_title': result['job_title'],
                            'location': result['location'],
                            'job_description': result['job_description'],
                            'job_url': result['job_url']
                        }
                        st.rerun()  # Refresh to populate fields
                    else:
                        st.error(f"❌ Could not fetch job details: {result['error']}")
                        st.info("💡 Try opening the job in your browser and copy the full description manually")
            except ImportError:
                st.error("LinkedIn fetcher module not found. Please enter details manually.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    elif fetch_clicked and not job_url:
        st.warning("⚠️ Please paste a LinkedIn URL first")
    
    st.divider()
    
    # Form for job details (populated from fetch or manual entry)
    with st.form("manual_job_form"):
        st.markdown("#### 📝 Job Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input(
                "🏢 Company Name *", 
                value=st.session_state.fetched_job.get('company_name', ''),
                placeholder="e.g., Microsoft, Google, Amazon"
            )
            location = st.text_input(
                "📍 Location", 
                value=st.session_state.fetched_job.get('location', ''),
                placeholder="e.g., Remote, New York, São Paulo"
            )
        
        with col2:
            job_title = st.text_input(
                "💼 Job Title *", 
                value=st.session_state.fetched_job.get('job_title', ''),
                placeholder="e.g., Senior Cloud Architect"
            )
            stored_url = st.text_input(
                "🔗 Job URL (for reference)",
                value=st.session_state.fetched_job.get('job_url', ''),
                placeholder="Will be filled automatically",
                disabled=True
            )
        
        job_description = st.text_area(
            "📋 Job Description *", 
            value=st.session_state.fetched_job.get('job_description', ''),
            placeholder="Paste the full job description here...\n\nInclude requirements, responsibilities, and qualifications for best CV tailoring.",
            height=300
        )
        
        st.divider()
        
        st.markdown("#### 📄 Choose CV Format")
        
        col_fmt1, col_fmt2, col_fmt3 = st.columns(3)
        
        with col_fmt1:
            generate_ats = st.form_submit_button(
                "📄 ATS PDF (B&W)", 
                use_container_width=True,
                help="Black & white, simple format - best for ATS systems"
            )
        
        with col_fmt2:
            generate_html = st.form_submit_button(
                "🌐 Premium HTML", 
                use_container_width=True,
                help="Colorful HTML format - great for email or web"
            )
        
        with col_fmt3:
            generate_pdf = st.form_submit_button(
                "✨ Premium PDF", 
                use_container_width=True,
                help="Fortune 500 quality PDF - best for direct submissions"
            )
    
    # Handle form submissions
    if generate_ats or generate_html or generate_pdf:
        # Validation
        if not company_name or not job_title or not job_description:
            st.error("⚠️ Please fill in Company Name, Job Title, and Job Description")
            return
        
        # Update session state so AI Analysis can access form data
        st.session_state.fetched_job.update({
            'company_name': company_name,
            'job_title': job_title,
            'job_description': job_description,
            'location': location
        })
        
        with st.spinner("🚀 Creating Fortune 500 quality CV... (15-30 seconds)"):

            try:
                from premium_cv_generator import PremiumCVGenerator
                gemini_key = st.session_state.get('gemini_api_key', '')
                generator = PremiumCVGenerator(gemini_api_key=gemini_key)
                
                job_data = {
                    'company_name': company_name,
                    'job_title': job_title,
                    'job_description': job_description,
                    'location': location,
                    'job_url': st.session_state.fetched_job.get('job_url', '')
                }
                
                result = generator.generate_tailored_cv(EMBEDDED_RESUME, job_data)
                
                st.success("✅ CV Generated Successfully!")
                
                # Determine which format was requested
                if generate_ats:
                    # ATS PDF (Black & White)
                    if result.get('ats_pdf_generated') and result.get('ats_pdf_path'):
                        with open(result['ats_pdf_path'], 'rb') as pdf_file:
                            pdf_data = pdf_file.read()
                        st.download_button(
                            label="📥 Download ATS PDF Resume (B&W)",
                            data=pdf_data,
                            file_name=f"Resume_ATS_{company_name}_{job_title[:20]}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                        st.caption(f"📁 Saved to: {result['ats_pdf_path']}")
                    else:
                        st.warning("ATS PDF not available, showing HTML version")
                        if result.get('ats_html'):
                            st.download_button(
                                label="📥 Download ATS HTML Resume",
                                data=result['ats_html'],
                                file_name=f"Resume_ATS_{company_name}_{job_title[:20]}.html",
                                mime="text/html"
                            )
                
                elif generate_html:
                    # Premium HTML
                    if result.get('premium_html'):
                        st.download_button(
                            label="📥 Download Premium HTML Resume",
                            data=result['premium_html'],
                            file_name=f"Resume_Premium_{company_name}_{job_title[:20]}.html",
                            mime="text/html",
                            type="primary"
                        )
                        if result.get('premium_html_path'):
                            st.caption(f"📁 Saved to: {result['premium_html_path']}")
                        
                        # Preview
                        with st.expander("👁️ Preview HTML Resume"):
                            st.components.v1.html(result['premium_html'], height=600, scrolling=True)
                
                elif generate_pdf:
                    # Premium PDF
                    if result.get('premium_pdf_generated') and result.get('premium_pdf_path'):
                        with open(result['premium_pdf_path'], 'rb') as pdf_file:
                            pdf_data = pdf_file.read()
                        st.download_button(
                            label="📥 Download Premium PDF Resume",
                            data=pdf_data,
                            file_name=f"Resume_Premium_{company_name}_{job_title[:20]}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                        st.caption(f"📁 Saved to: {result['premium_pdf_path']}")
                    else:
                        st.warning("Premium PDF not available, showing HTML version")
                        if result.get('premium_html'):
                            st.download_button(
                                label="📥 Download Premium HTML Resume",
                                data=result['premium_html'],
                                file_name=f"Resume_Premium_{company_name}_{job_title[:20]}.html",
                                mime="text/html"
                            )
                
                # Show all generated files
                st.divider()
                st.markdown("#### 📁 All Generated Files")
                files_generated = []
                if result.get('ats_pdf_path'):
                    files_generated.append(f"- ATS PDF: `{result['ats_pdf_path']}`")
                if result.get('ats_html_path'):
                    files_generated.append(f"- ATS HTML: `{result['ats_html_path']}`")
                if result.get('premium_html_path'):
                    files_generated.append(f"- Premium HTML: `{result['premium_html_path']}`")
                if result.get('premium_pdf_path'):
                    files_generated.append(f"- Premium PDF: `{result['premium_pdf_path']}`")
                
                if files_generated:
                    st.markdown("\n".join(files_generated))
                
                st.info(f"💡 Tokens used: {result.get('tokens_used', 'N/A')}")
                
            except Exception as e:
                st.error(f"❌ Error generating CV: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # ============================================================
    # AI ANALYSIS SECTION - Dynamic Model Discovery
    # ============================================================
    st.divider()
    st.markdown("### 🤖 AI Job Fit Analysis")
    st.markdown("""
    Get an **in-depth analysis** of your fit for this position using AI.
    Enter API keys to discover available models, then choose any models you want for analysis.
    """)
    
    # Initialize session state for discovered models
    if 'discovered_openai_models' not in st.session_state:
        st.session_state.discovered_openai_models = []
    if 'discovered_gemini_models' not in st.session_state:
        st.session_state.discovered_gemini_models = []
    if 'selected_models' not in st.session_state:
        st.session_state.selected_models = []
    
    # API Keys section
    st.markdown("#### 🔑 Step 1: Enter API Keys")
    col_key1, col_key2 = st.columns(2)
    
    with col_key1:
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Enter to discover available OpenAI models",
            key="ai_analysis_openai_key"
        )
        
        if st.button("🔍 Discover OpenAI Models", key="discover_openai"):
            if openai_key:
                with st.spinner("Discovering OpenAI models..."):
                    try:
                        from multi_ai_analyzer import discover_openai_models
                        result = discover_openai_models(openai_key)
                        if result['success']:
                            st.session_state.discovered_openai_models = result['models']
                            st.success(f"✅ Found {len(result['models'])} OpenAI models!")
                        else:
                            st.error(f"❌ {result['error']}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter an OpenAI API key first")
    
    with col_key2:
        gemini_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Enter to discover available Gemini models",
            key="ai_analysis_gemini_key"
        )
        
        if st.button("🔍 Discover Gemini Models", key="discover_gemini"):
            if gemini_key:
                with st.spinner("Discovering Gemini models..."):
                    try:
                        from multi_ai_analyzer import discover_gemini_models
                        result = discover_gemini_models(gemini_key)
                        if result['success']:
                            st.session_state.discovered_gemini_models = result['models']
                            st.success(f"✅ Found {len(result['models'])} Gemini models!")
                        else:
                            st.error(f"❌ {result['error']}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a Gemini API key first")
    
    # Model Selection section
    st.markdown("#### 🎯 Step 2: Select Models to Use")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("**OpenAI Models:**")
        if st.session_state.discovered_openai_models:
            openai_model_options = [m['id'] for m in st.session_state.discovered_openai_models]
            selected_openai = st.multiselect(
                "Select OpenAI models",
                options=openai_model_options,
                default=[],
                help="Select one or more OpenAI models",
                key="selected_openai_models"
            )
        else:
            st.info("👆 Click 'Discover OpenAI Models' after entering API key")
            selected_openai = []
    
    with col_m2:
        st.markdown("**Gemini Models:**")
        if st.session_state.discovered_gemini_models:
            gemini_model_options = [m['id'] for m in st.session_state.discovered_gemini_models]
            selected_gemini = st.multiselect(
                "Select Gemini models",
                options=gemini_model_options,
                default=[],
                help="Select one or more Gemini models",
                key="selected_gemini_models"
            )
        else:
            st.info("👆 Click 'Discover Gemini Models' after entering API key")
            selected_gemini = []
    
    # Rate Limit Status
    with st.expander("📊 Rate Limit Status", expanded=False):
        try:
            from multi_ai_analyzer import get_rate_limit_status
            rate_status = get_rate_limit_status()
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("**OpenAI:**")
                openai_stats = rate_status['openai']
                st.caption(f"Requests: {openai_stats['requests_last_minute']}/{openai_stats['limits']['requests_per_minute']} per min | "
                          f"{openai_stats['requests_last_hour']}/{openai_stats['limits']['requests_per_hour']} per hour | "
                          f"{openai_stats['requests_last_day']}/{openai_stats['limits']['requests_per_day']} per day")
            with col_r2:
                st.markdown("**Gemini:**")
                gemini_stats = rate_status['gemini']
                st.caption(f"Requests: {gemini_stats['requests_last_minute']}/{gemini_stats['limits']['requests_per_minute']} per min | "
                          f"{gemini_stats['requests_last_hour']}/{gemini_stats['limits']['requests_per_hour']} per hour | "
                          f"{gemini_stats['requests_last_day']}/{gemini_stats['limits']['requests_per_day']} per day")
        except:
            st.info("Rate limit status will be available after first analysis")
    
    # Build models list for analysis
    models_to_analyze = []
    for model_id in selected_openai:
        models_to_analyze.append({'provider': 'openai', 'model': model_id})
    for model_id in selected_gemini:
        models_to_analyze.append({'provider': 'gemini', 'model': model_id})
    
    # Run Analysis button
    st.markdown("#### 🚀 Step 3: Run Analysis")
    
    if st.button("🧠 Run AI Analysis", use_container_width=True, type="primary", key="run_ai_analysis"):
        # Get current job data from session state
        current_company = st.session_state.fetched_job.get('company_name', '')
        current_title = st.session_state.fetched_job.get('job_title', '')
        current_description = st.session_state.fetched_job.get('job_description', '')
        
        if not current_company or not current_title or not current_description:
            st.error("⚠️ Please fill in Company Name, Job Title, and Job Description first")
            st.info("💡 Use the form above to enter job details or fetch from LinkedIn URL")
        elif not models_to_analyze:
            st.warning("⚠️ Please select at least one model to run analysis")
        else:
            with st.spinner(f"🧠 Analyzing with {len(models_to_analyze)} model(s)... (10-60 seconds)"):
                try:
                    from multi_ai_analyzer import MultiAIAnalyzer
                    
                    analyzer = MultiAIAnalyzer(
                        openai_key=openai_key if openai_key else None,
                        gemini_key=gemini_key if gemini_key else None
                    )
                    
                    job_data = {
                        'company_name': current_company,
                        'job_title': current_title,
                        'job_description': current_description
                    }
                    
                    results = analyzer.analyze_job(job_data, EMBEDDED_RESUME, models=models_to_analyze)
                    
                    # FALLBACK LOGIC: If all results failed, try alternate provider
                    all_failed = all(r.error is not None for r in results.values()) if results else True
                    
                    if all_failed:
                        # Determine which provider(s) failed
                        failed_providers = set(m['provider'] for m in models_to_analyze)
                        
                        # Try alternate provider as fallback
                        fallback_models = []
                        
                        if 'openai' in failed_providers and gemini_key:
                            # OpenAI failed, try Gemini
                            st.warning("⚠️ OpenAI failed, trying Gemini as fallback...")
                            if st.session_state.discovered_gemini_models:
                                # Use first available Gemini model
                                fallback_models.append({
                                    'provider': 'gemini', 
                                    'model': st.session_state.discovered_gemini_models[0]['id']
                                })
                            else:
                                # Default fallback model
                                fallback_models.append({'provider': 'gemini', 'model': 'gemini-2.0-flash'})
                        
                        elif 'gemini' in failed_providers and openai_key:
                            # Gemini failed, try OpenAI
                            st.warning("⚠️ Gemini failed, trying OpenAI as fallback...")
                            if st.session_state.discovered_openai_models:
                                fallback_models.append({
                                    'provider': 'openai',
                                    'model': st.session_state.discovered_openai_models[0]['id']
                                })
                            else:
                                fallback_models.append({'provider': 'openai', 'model': 'gpt-4o-mini'})
                        
                        if fallback_models:
                            fallback_results = analyzer.analyze_job(job_data, EMBEDDED_RESUME, models=fallback_models)
                            results.update(fallback_results)
                    
                    consensus = analyzer.get_consensus(results)
                    
                    # Display results
                    st.success("✅ Analysis Complete!")

                    
                    # Consensus summary (if multiple models)
                    if len(results) > 1:
                        st.markdown("#### 📊 Consensus Summary")
                        
                        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                        with col_c1:
                            st.metric("Average Score", f"{consensus['average_score']}%")
                        with col_c2:
                            st.metric("Score Range", f"{consensus['min_score']}-{consensus['max_score']}")
                        with col_c3:
                            qualified_text = "Yes ✅" if consensus['consensus_qualified'] else "No ❌"
                            st.metric("Qualified", qualified_text)
                        with col_c4:
                            agreement_emoji = {"high": "🟢", "moderate": "🟡", "low": "🔴"}.get(consensus['agreement_level'], "⚪")
                            st.metric("Agreement", f"{agreement_emoji} {consensus['agreement_level'].title()}")
                        
                        st.divider()
                    
                    # Individual results
                    st.markdown("#### 📋 Individual AI Assessments")
                    
                    for provider_name, result in results.items():
                        with st.expander(f"**{provider_name}** - Score: {result.score}% {'✅' if result.qualified else '❌'}", expanded=True):
                            if result.error:
                                st.error(f"Error: {result.error}")
                            else:
                                # Score and qualification
                                col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
                                with col_s1:
                                    score_color = "green" if result.score >= 75 else "orange" if result.score >= 50 else "red"
                                    st.markdown(f"### :{score_color}[{result.score}%]")
                                with col_s2:
                                    st.markdown(f"**Justification:** {result.justification}")
                                with col_s3:
                                    st.caption(f"⏱️ {result.processing_time_ms}ms | 🎟️ ~{result.tokens_used} tokens")
                                # NEW COMPREHENSIVE DISPLAY
                                
                                # Executive Summary & Recommendation
                                if result.recommendation:
                                    rec_color = {"STRONG MATCH": "green", "GOOD MATCH": "blue", "PARTIAL MATCH": "orange", "WEAK MATCH": "red", "NOT RECOMMENDED": "red"}.get(result.recommendation, "gray")
                                    st.markdown(f"**Recommendation:** :{rec_color}[{result.recommendation}]")
                                
                                if result.executive_summary:
                                    st.info(f"📋 **Executive Summary:** {result.executive_summary}")
                                elif result.justification:
                                    st.info(f"📋 **Summary:** {result.justification}")
                                
                                # Section-by-Section Evaluations with justifications
                                if result.section_evaluations:
                                    st.markdown("---")
                                    st.markdown("### 📊 Section-by-Section Evaluation")
                                    
                                    section_labels = {
                                        'technical_skills': ('🔧 Technical Skills', 'Technical capabilities and tools'),
                                        'experience_level': ('📈 Experience Level', 'Years and seniority alignment'),
                                        'industry_domain': ('🏭 Industry/Domain', 'Industry experience match'),
                                        'leadership_management': ('👔 Leadership', 'Management capabilities'),
                                        'certifications_education': ('🏅 Certifications', 'Required credentials'),
                                        'cloud_platforms': ('☁️ Cloud Platforms', 'Cloud expertise'),
                                        'soft_skills': ('💬 Soft Skills', 'Communication & collaboration'),
                                        'location_arrangement': ('📍 Location', 'Work arrangement fit')
                                    }
                                    
                                    for section_key, (label, tooltip) in section_labels.items():
                                        section_data = result.section_evaluations.get(section_key, {})
                                        if section_data:
                                            score = section_data.get('score', 0)
                                            justification = section_data.get('justification', '')
                                            matches = section_data.get('matches', [])
                                            gaps = section_data.get('gaps', [])
                                            
                                            score_color = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
                                            
                                            with st.expander(f"{score_color} {label}: **{score}%**"):
                                                if justification:
                                                    st.markdown(f"**Justification:** {justification}")
                                                if matches:
                                                    st.markdown("**✅ Matches:**")
                                                    for m in matches[:5]:
                                                        st.markdown(f"  - {m}")
                                                if gaps:
                                                    st.markdown("**⚠️ Gaps:**")
                                                    for g in gaps[:5]:
                                                        st.markdown(f"  - {g}")
                                
                                # Also show legacy section scores if section_evaluations not available
                                elif result.section_scores:
                                    st.markdown("**Section Scores:**")
                                    section_names = {
                                        'technical_skills': '🔧 Technical',
                                        'experience_level': '📈 Experience',
                                        'industry_match': '🏭 Industry',
                                        'leadership': '👔 Leadership',
                                        'certifications': '🏅 Certifications'
                                    }
                                    cols = st.columns(5)
                                    for i, (key, lbl) in enumerate(section_names.items()):
                                        sc = result.section_scores.get(key, 0)
                                        cols[i].metric(lbl, f"{sc}%")
                                
                                st.markdown("---")
                                
                                # Key Strengths and Critical Gaps
                                col_m, col_g = st.columns(2)
                                with col_m:
                                    st.markdown("**💪 Key Strengths:**")
                                    strengths = result.key_strengths if result.key_strengths else result.key_matches
                                    if strengths:
                                        for strength in strengths[:5]:
                                            st.markdown(f"- {strength}")
                                    else:
                                        st.caption("No specific strengths identified")
                                
                                with col_g:
                                    st.markdown("**⚠️ Critical Gaps:**")
                                    critical_gaps = result.critical_gaps if result.critical_gaps else result.gaps
                                    if critical_gaps:
                                        for gap in critical_gaps[:5]:
                                            st.markdown(f"- {gap}")
                                    else:
                                        st.caption("No critical gaps identified")
                                
                                # Interview Talking Points 
                                if result.interview_talking_points:
                                    st.markdown("---")
                                    st.markdown("**🎯 Interview Talking Points:**")
                                    for point in result.interview_talking_points[:5]:
                                        st.markdown(f"- {point}")
                                
                                # CV Enhancement Suggestions
                                if result.cv_enhancement_suggestions:
                                    st.markdown("---")
                                    st.markdown("**✍️ CV Enhancement Suggestions:**")
                                    for suggestion in result.cv_enhancement_suggestions[:5]:
                                        st.markdown(f"- {suggestion}")

                    
                    # Store results in session state
                    st.session_state['ai_analysis_results'] = {
                        'results': {k: v.to_dict() for k, v in results.items()},
                        'consensus': consensus
                    }
                    
                except ImportError as e:
                    st.error(f"❌ Missing module: {str(e)}")
                    st.info("💡 Make sure multi_ai_analyzer.py is in the project directory")
                except Exception as e:
                    st.error(f"❌ Error during analysis: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())


def render_all_jobs(db):
    """Render all jobs browser with filters"""
    st.markdown("### 📋 All Jobs Browser")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search = st.text_input("🔍 Search", placeholder="Job title, company, or keywords...")
    
    with col2:
        status_filter = st.selectbox("Status", ['All', 'Pending', 'Qualified', 'Low_score', 'Error'])
    
    with col3:
        work_type_filter = st.selectbox("Work Type", ['All', 'Remote', 'Hybrid', 'On-site'])
    
    with col4:
        sort_by = st.selectbox("Sort By", ['Most Recent', 'Highest Score', 'Company', 'Job Title', 'Posted Date'])
    
    col5, col6 = st.columns(2)
    with col5:
        min_score = st.slider("Minimum Score", 0, 100, 0)
    with col6:
        easy_apply = st.checkbox("Easy Apply Only")
    
    # Build filters dict
    filters = {
        'search': search,
        'status': status_filter,
        'work_type': work_type_filter,
        'min_score': min_score if min_score > 0 else None,
        'has_easy_apply': easy_apply,
        'sort_by': sort_by
    }
    
    # Pagination
    page_size = 25
    total_count = db.get_jobs_count(filters)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    
    if 'jobs_page' not in st.session_state:
        st.session_state.jobs_page = 0
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("⬅️ Previous") and st.session_state.jobs_page > 0:
            st.session_state.jobs_page -= 1
    with col2:
        st.markdown(f"**Page {st.session_state.jobs_page + 1} of {total_pages}** ({total_count} jobs)")
    with col3:
        if st.button("Next ➡️") and st.session_state.jobs_page < total_pages - 1:
            st.session_state.jobs_page += 1
    
    # Get jobs
    jobs_df = db.get_all_jobs(filters, limit=page_size, offset=st.session_state.jobs_page * page_size)
    
    if jobs_df.empty:
        st.info("No jobs found matching your criteria.")
        return
    
    # Export Section
    st.markdown("---")
    st.markdown("#### 📤 Export Filtered Results")
    col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
    
    with col_exp1:
        st.caption(f"Export all {total_count} jobs matching your filters")
    
    with col_exp2:
        if st.button("📥 Export CSV", key="export_csv_all", use_container_width=True):
            # Get all jobs matching filters for export (not just current page)
            export_df = db.get_all_jobs(filters, limit=1000, offset=0)
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"all_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv_all"
            )
    
    with col_exp3:
        if st.button("📊 Export Excel", key="export_excel_all", use_container_width=True):
            import io
            # Get all jobs matching filters for export
            export_df = db.get_all_jobs(filters, limit=1000, offset=0)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='All Jobs')
            excel_data = buffer.getvalue()
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_data,
                file_name=f"all_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_all"
            )
    
    st.markdown("---")
    for _, job in jobs_df.iterrows():
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Title and company
                title = job['title'] or 'Unknown Position'
                company = job['company'] or 'Unknown Company'
                st.markdown(f"**{title}**")
                st.caption(f"🏢 {company} | 📍 {job['location'] or 'N/A'}")
                
                # Badges
                badges = []
                if job['work_type'] and 'remote' in str(job['work_type']).lower():
                    badges.append('<span class="remote-badge">🏠 Remote</span>')
                if job['apply_url']:
                    badges.append('<span class="easy-apply">⚡ Easy Apply</span>')
                if job['salary']:
                    badges.append(f"💰 {job['salary']}")
                
                if badges:
                    st.markdown(' '.join(badges), unsafe_allow_html=True)
            
            with col2:
                if job['score'] is not None:
                    if job['score'] >= 70:
                        st.markdown(f'<span class="qualified-badge">{job["score"]}%</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="rejected-badge">{job["score"]}%</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="pending-badge">{job["status"]}</span>', unsafe_allow_html=True)
                
                if job['job_url']:
                    st.link_button("View →", job['job_url'], use_container_width=True)
            
            st.divider()


def render_csv_upload(db):
    """Render CSV upload section"""
    st.markdown("### 📤 Import Jobs from CSV")
    
    st.info("""
    Upload CSV files exported from LinkedIn job scrapers. 
    Required columns: `job_title`, `company_name`, `job_description`, `job_url`
    Optional: `location`, `salary_info`, `work_type`, `apply_url`
    """)
    
    uploaded_files = st.file_uploader(
        "Drop CSV files here",
        type=['csv'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"📄 **{uploaded_file.name}**")
            
            # Preview
            try:
                content = uploaded_file.read().decode('utf-8')
                uploaded_file.seek(0)  # Reset for later use
                
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
                st.caption(f"Found {len(rows)} jobs in file")
                
                # Show preview
                if rows:
                    preview_df = pd.DataFrame(rows[:5])
                    st.dataframe(preview_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        if st.button("🚀 Import All Jobs", type="primary"):
            total_imported = 0
            total_skipped = 0
            
            for uploaded_file in uploaded_files:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    imported, skipped = db.import_jobs_from_csv(content)
                    total_imported += imported
                    total_skipped += skipped
                    st.success(f"✅ {uploaded_file.name}: Imported {imported}, Skipped {skipped} duplicates")
                except Exception as e:
                    st.error(f"❌ {uploaded_file.name}: {e}")
            
            st.balloons()
            st.success(f"🎉 Total: Imported {total_imported} jobs, Skipped {total_skipped} duplicates")


def render_top_companies(db):
    """Render top companies chart"""
    st.markdown("### 🏢 Top Companies")
    
    companies_df = db.get_top_companies(10)
    
    if companies_df.empty:
        st.info("No company data yet")
        return
    
    fig = px.bar(
        companies_df.head(10),
        x='qualified',
        y='company',
        orientation='h',
        color='avg_score',
        color_continuous_scale='Greens'
    )
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)


def main():
    """Main dashboard entry point"""
    
    # Initialize database connection
    db = DatabaseConnection()
    
    if not db.conn:
        st.error("❌ Cannot connect to database. Make sure PostgreSQL is running.")
        st.code("docker-compose -f docker-compose.postgres.yml up -d", language="bash")
        return
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("## 🎯 Navigation")
        page = st.radio(
            "Go to",
            ["📊 Dashboard", "📋 All Jobs", "🌟 Qualified Jobs", "🔗 Manual Job CV", "📤 Import CSV"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.markdown("## ⚙️ Controls")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        if auto_refresh:
            time.sleep(30)
            st.rerun()
        
        st.markdown("---")
        
        # Quick Stats
        stats = db.get_stats()
        if stats:
            st.markdown("## 📊 Quick Stats")
            st.markdown(f"- **Total Jobs:** {stats['total']}")
            st.markdown(f"- **Pending:** {stats['pending']}")
            st.markdown(f"- **Qualified:** {stats['qualified']}")
            st.markdown(f"- **Errors:** {stats['errors']}")
        
        st.markdown("---")
        
        st.markdown("## 🔗 Links")
        st.markdown("- [Metabase Dashboard](http://localhost:3000)")
        st.markdown("- [Google Drive Resumes](https://drive.google.com)")
    
    # Main content based on page selection
    render_header()
    
    if page == "📊 Dashboard":
        stats = db.get_stats()
        if stats:
            render_metrics(stats)
            st.divider()
            render_progress_bar(stats)
            st.divider()
            render_charts(db)
            st.divider()
            
            tab1, tab2 = st.tabs(["📝 Recent Activity", "🏢 Top Companies"])
            with tab1:
                render_recent_activity(db)
            with tab2:
                render_top_companies(db)
    
    elif page == "📋 All Jobs":
        render_all_jobs(db)
    
    elif page == "🌟 Qualified Jobs":
        render_qualified_jobs(db)
    
    elif page == "🔗 Manual Job CV":
        render_manual_job_cv()
    
    elif page == "📤 Import CSV":
        render_csv_upload(db)


if __name__ == "__main__":
    main()
