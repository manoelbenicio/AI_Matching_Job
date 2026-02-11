# RFP Automation Platform — Solution Architecture Document

> **Document Version**: 2.0  
> **Date**: 2026-02-10  
> **Author**: DataOps Team  
> **Status**: Production  
> **Host Machine**: `msi-laptop` — Windows 10/11, IP `192.168.16.111`

---

## 1. Executive Summary

The **RFP Automation Platform** is a Windows-based development workstation (`msi-laptop`) hosting three independent sub-systems under a single repository (`D:\VMs\Projetos\RFP_Automation_VF`). The primary active system is the **AI Job Matcher**, which processes LinkedIn job postings, scores candidate-job fit using AI, and generates tailored resumes.

### Sub-System Inventory

| # | Sub-System | Path | Status | Purpose |
|---|------------|------|--------|---------|
| 1 | **AI Job Matcher** | `AI_Job_Matcher\` | ✅ Active (Production) | Job scoring, CV generation, Streamlit dashboard |
| 2 | **LinkedIn Scrapper** | `Linkedin_Scrapper\` | ⏸️ Stopped | Legacy n8n-based LinkedIn scraping pipeline |
| 3 | **RFP Automation** | `RFP_Automation\` | 📦 Archived | RFI/RFP pricing solution with AI |
| 4 | **Generico_Laptop** | `Generico_Laptop\` | 📦 Static | Reference RFI documents (Minsait/Vivo) |

---

## 2. High-Level Architecture (AS-IS)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  HOST: msi-laptop (192.168.16.111) — Windows — D:\VMs\Projetos\RFP_Automation_VF │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  ┌───────────────────── AI_Job_Matcher (ACTIVE) ──────────────────────────────┐  │
│  │                                                                             │  │
│  │  ┌─────────────────── Python Layer (.venv) ──────────────────────────────┐  │  │
│  │  │  job_matcher.py          — Core scorer + resume pipeline              │  │  │
│  │  │  multi_ai_analyzer.py    — Multi-AI analysis (OpenAI + Gemini)        │  │  │
│  │  │  premium_cv_generator.py — PDF CV generation                          │  │  │
│  │  │  linkedin_job_fetcher.py — LinkedIn job scraping                      │  │  │
│  │  │  dashboard.py (88 KB)    — Streamlit real-time dashboard              │  │  │
│  │  │  export_to_excel.py      — Excel report exporter                      │  │  │
│  │  │  import_jobs_smart.py    — Smart job import utility                   │  │  │
│  │  │  import_sheets_to_postgres.py — Google Sheets migration              │  │  │
│  │  │  reprocess_scored_jobs.py — Re-scoring utility                       │  │  │
│  │  │  discard_technical_jobs.py — Job filtering utility                   │  │  │
│  │  │  migrate_from_linkedin_db.py — Cross-DB migration                   │  │  │
│  │  └───────────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                              │  │
│  │                              ▼                                              │  │
│  │  ┌───────────── Docker Network: job_matcher_network ─────────────────────┐  │  │
│  │  │                  Subnet: 172.20.0.0/16                                 │  │  │
│  │  │                  Gateway: 172.20.0.1                                    │  │  │
│  │  │                                                                        │  │  │
│  │  │  ┌──── job_matcher_postgres ────┐   ┌──── job_matcher_metabase ─────┐  │  │  │
│  │  │  │  postgres:15-alpine          │   │  metabase/metabase:v0.48.0    │  │  │  │
│  │  │  │  IP: 172.20.0.2              │   │  IP: 172.20.0.3              │  │  │  │
│  │  │  │  Port: 5432 → 0.0.0.0:5432  │◄─►│  Port: 3000 → 0.0.0.0:3000  │  │  │  │
│  │  │  │  DB: job_matcher             │   │  Analytics Dashboard         │  │  │  │
│  │  │  │  User: job_matcher           │   │                               │  │  │  │
│  │  │  │  Vol: postgres_data          │   │  Vol: metabase_data           │  │  │  │
│  │  │  └──────────────────────────────┘   └───────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                             │  │
│  │  ┌───────────── Streamlit Dashboard ─────────────────────────────────────┐  │  │
│  │  │  Port: 8501 → 0.0.0.0:8501  │  Process: .venv\Scripts\streamlit.exe  │  │  │
│  │  └───────────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
│  ┌───────────── Linkedin_Scrapper (STOPPED) ──────────────────────────────────┐  │
│  │  Network: job-automation-network (bridge, no IPAM)                          │  │
│  │  Containers (ALL STOPPED):                                                  │  │
│  │    job-automation-db       — postgres:15-alpine  — Port 5432 (CONFLICT)    │  │
│  │    job-automation-api      — Node.js backend     — Port 3001               │  │
│  │    job-automation-frontend — React/Vite frontend — Port 5173               │  │
│  │    job-automation-n8n      — n8nio/n8n:latest    — Port 5678               │  │
│  │    job-automation-scraper  — Python scraper       — Port 8000               │  │
│  │  Volumes: linkedin_scrapper_postgres_data, linkedin_scrapper_n8n_data      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
└──────────────────────────────────────────────────────────────────────────────────┘
                                      │
                        ┌─────────────┼─────────────┐
                        ▼             ▼             ▼
                 ┌────────────┐ ┌──────────┐ ┌──────────────┐
                 │  OpenAI    │ │ Google   │ │  Telegram    │
                 │  API       │ │ APIs     │ │  Bot API     │
                 │ gpt-4o-mini│ │ Docs/    │ │              │
                 │            │ │ Drive/   │ │              │
                 │            │ │ Sheets   │ │              │
                 └────────────┘ └──────────┘ └──────────────┘
```

---

## 3. Component Catalog

### 3.1 AI Job Matcher — Application Components

| Component | File | Size | Technology | Purpose |
|-----------|------|------|------------|---------|
| **Core Scorer** | `job_matcher.py` | 43 KB | Python + OpenAI | Main pipeline: fetch → score → qualify → enhance |
| **Multi-AI Analyzer** | `multi_ai_analyzer.py` | 47 KB | Python + OpenAI + Gemini | Parallel AI analysis with multiple providers |
| **Premium CV Generator** | `premium_cv_generator.py` | 32 KB | Python + pdfkit | Generate tailored PDF resumes |
| **LinkedIn Fetcher** | `linkedin_job_fetcher.py` | 9 KB | Python + BeautifulSoup | Scrape job details from LinkedIn URLs |
| **Streamlit Dashboard** | `dashboard.py` | 88 KB | Python + Streamlit + Plotly | Real-time monitoring web UI |
| **Excel Exporter** | `export_to_excel.py` | 5 KB | Python + Pandas + openpyxl | Export qualified jobs to `.xlsx` |
| **Smart Importer** | `import_jobs_smart.py` | 14 KB | Python | Intelligent job import with deduplication |
| **Sheets Migrator** | `import_sheets_to_postgres.py` | 9 KB | Python + Google API | Migrate historical data from Google Sheets |
| **Job Reprocessor** | `reprocess_scored_jobs.py` | 8 KB | Python | Re-score previously processed jobs |
| **Technical Filter** | `discard_technical_jobs.py` | 4 KB | Python | Filter out irrelevant technical roles |
| **DB Migrator** | `migrate_from_linkedin_db.py` | 5 KB | Python | Cross-database migration utility |
| **Batch Runner** | `run_batch_score.py` | 1 KB | Python | Batch scoring launcher |
| **Excel Checker** | `check_excel.py` | 1 KB | Python | Validate Excel file integrity |

### 3.2 AI Job Matcher — Infrastructure Components

| Component | Container Name | Image | IP Address | Host Port | Volume |
|-----------|---------------|-------|------------|-----------|--------|
| **PostgreSQL 15** | `job_matcher_postgres` | `postgres:15-alpine` | `172.20.0.2` | `5432` | `ai_job_matcher_postgres_data` |
| **Metabase** | `job_matcher_metabase` | `metabase/metabase:v0.48.0` | `172.20.0.3` | `3000` | `ai_job_matcher_metabase_data` |

### 3.3 LinkedIn Scrapper — Infrastructure Components (STOPPED)

| Component | Container Name | Image | Host Port | Volume |
|-----------|---------------|-------|-----------|--------|
| **PostgreSQL 15** | `job-automation-db` | `postgres:15-alpine` | `5432` ⚠️ | `linkedin_scrapper_postgres_data` |
| **Node.js API** | `job-automation-api` | Custom Dockerfile | `3001` | bind mount `./backend` |
| **React Frontend** | `job-automation-frontend` | Custom Dockerfile | `5173` | bind mount `./frontend` |
| **n8n Workflows** | `job-automation-n8n` | `n8nio/n8n:latest` | `5678` | `linkedin_scrapper_n8n_data` |
| **Python Scraper** | `job-automation-scraper` | Custom Dockerfile | `8000` | — |

> [!WARNING]
> LinkedIn Scrapper's PostgreSQL also maps to host port 5432. Both stacks **cannot run simultaneously** without port remapping.

### 3.4 External Services

| Service | Provider | Used By | Authentication | Endpoint |
|---------|----------|---------|----------------|----------|
| **OpenAI API** | OpenAI | `job_matcher.py`, `multi_ai_analyzer.py` | API Key (`sk-proj-...`) | `api.openai.com` |
| **Google Gemini** | Google | `multi_ai_analyzer.py`, `premium_cv_generator.py` | API Key | `generativelanguage.googleapis.com` |
| **Google Docs API** | Google | `job_matcher.py` | OAuth 2.0 | `docs.googleapis.com` |
| **Google Drive API** | Google | `job_matcher.py` | OAuth 2.0 | `drive.googleapis.com` |
| **Google Sheets API** | Google | `import_sheets_to_postgres.py` | OAuth 2.0 | `sheets.googleapis.com` |
| **Telegram Bot** | Telegram | `job_matcher.py` | Bot Token | `api.telegram.org` |

---

## 4. Network Architecture

### 4.1 Host Machine

| Property | Value |
|----------|-------|
| Hostname | `msi-laptop` |
| OS | Windows 10/11 |
| Wi-Fi IP | `192.168.16.111` |
| WSL/Docker IPs | `172.23.160.1`, `172.26.0.1` |
| Docker Engine | Docker Desktop for Windows |

### 4.2 Docker Networks

| Network Name | Driver | Subnet | Gateway | Used By |
|--------------|--------|--------|---------|---------|
| `job_matcher_network` | bridge | `172.20.0.0/16` | `172.20.0.1` | AI Job Matcher |
| `job-automation-network` | bridge | Auto-assigned | Auto | LinkedIn Scrapper (stopped) |
| `bridge` | bridge | Default | — | System default |

### 4.3 Port Allocation Map

| Host Port | Protocol | Service | Container | Stack |
|-----------|----------|---------|-----------|-------|
| **3000** | HTTP | Metabase Dashboard | `job_matcher_metabase` | AI Job Matcher |
| **5432** | TCP | PostgreSQL | `job_matcher_postgres` | AI Job Matcher ✅ |
| **5432** | TCP | PostgreSQL | `job-automation-db` | LinkedIn Scrapper ⚠️ CONFLICT |
| **8501** | HTTP | Streamlit Dashboard | host process | AI Job Matcher |
| **3001** | HTTP | Node.js API | `job-automation-api` | LinkedIn Scrapper (stopped) |
| **5173** | HTTP | React Frontend | `job-automation-frontend` | LinkedIn Scrapper (stopped) |
| **5678** | HTTP | n8n Workflow Engine | `job-automation-n8n` | LinkedIn Scrapper (stopped) |
| **8000** | HTTP | Python Scraper | `job-automation-scraper` | LinkedIn Scrapper (stopped) |

### 4.4 Docker Volumes

| Volume Name | Driver | Used By | Purpose |
|-------------|--------|---------|---------|
| `ai_job_matcher_postgres_data` | local | `job_matcher_postgres` | Job Matcher DB persistence |
| `ai_job_matcher_metabase_data` | local | `job_matcher_metabase` | Metabase config + H2 DB |
| `linkedin_scrapper_postgres_data` | local | `job-automation-db` | LinkedIn Scrapper DB persistence |
| `linkedin_scrapper_n8n_data` | local | `job-automation-n8n` | n8n workflows + credentials |

---

## 5. Database Architecture

### 5.1 AI Job Matcher Database (`job_matcher`)

| Property | Value |
|----------|-------|
| Engine | PostgreSQL 15 (Alpine) |
| Database | `job_matcher` |
| User | `job_matcher` |
| Password | `JobMatcher2024!` |
| Connection (from host) | `postgresql://job_matcher:JobMatcher2024!@127.0.0.1:5432/job_matcher` |
| Connection (container-to-container) | `postgresql://job_matcher:JobMatcher2024!@job_matcher_postgres:5432/job_matcher` |
| Extensions | `pg_trgm` (fuzzy text search) |

#### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `jobs` | Primary job storage | `job_id`, `job_title`, `company_name`, `score`, `status`, `job_description`, `job_url`, `custom_resume_url` |
| `ai_analyses` | AI scoring history | `analysis_id`, `job_id`, `ai_provider`, `model_used`, `score`, `analysis_json` |
| `batch_runs` | Batch processing log | `batch_id`, `started_at`, `completed_at`, `total_jobs`, `qualified_count` |
| `processing_logs` | Operation audit trail | `log_id`, `operation`, `status`, `details`, `created_at` |
| `schema_migrations` | Migration version tracking | `version`, `applied_at` |

#### Views

| View | Purpose |
|------|---------|
| `v_qualified_jobs` | Jobs with score ≥ 75, status = `qualified` or `enhanced` |
| `v_daily_stats` | Daily aggregated scoring statistics |
| `v_analysis_comparison` | Side-by-side AI provider analysis comparison |

#### Data States (Job Lifecycle)

```
  pending → processing → qualified (≥75%) → enhanced (CV generated)
                ↓              ↓
            error          low_score (<75%)
```

| State | Description | Next Action |
|-------|-------------|-------------|
| `pending` | New job awaiting processing | AI scoring |
| `processing` | Currently being scored | Wait |
| `qualified` | Score ≥ 75% | Resume generation |
| `enhanced` | Custom resume generated & uploaded | Ready to apply |
| `low_score` | Score < 75% | Archive |
| `error` | Processing failed | Retry or manual review |

### 5.2 LinkedIn Scrapper Database (`linkedin_jobs`)

| Property | Value |
|----------|-------|
| Database | `linkedin_jobs` |
| n8n Database | `n8n` (separate DB in same instance) |
| User | `n8n_user` |
| Password | `n8n_secure_pass_2024` |

---

## 6. Configuration & Secrets

### 6.1 AI Job Matcher `.env`

| Variable | Category | Value / Pattern |
|----------|----------|-----------------|
| `DB_HOST` | Database | `127.0.0.1` |
| `DB_PORT` | Database | `5432` |
| `DB_NAME` | Database | `job_matcher` |
| `DB_USER` | Database | `job_matcher` |
| `DB_PASSWORD` | Database | `JobMatcher2024!` |
| `DATABASE_URL` | Database | `postgresql://...@127.0.0.1:5432/job_matcher` |
| `OPENAI_API_KEY` | AI | `sk-proj-...` (OpenAI project key) |
| `OPENAI_MODEL` | AI | `gpt-4o-mini` |
| `TELEGRAM_BOT_TOKEN` | Notifications | `8522325100:AAG...` |
| `TELEGRAM_CHAT_ID` | Notifications | `999264527` |
| `RESUME_DOC_ID` | Google Docs | `1qdjw...` (base resume template) |
| `RESUME_FOLDER_ID` | Google Drive | `1yicu...` (generated CVs folder) |

### 6.2 LinkedIn Scrapper `.env`

| Variable | Category | Value / Pattern |
|----------|----------|-----------------|
| `DB_USER` | Database | `n8n_user` |
| `DB_PASSWORD` | Database | `n8n_secure_pass_2024` |
| `DB_NAME` | Database | `linkedin_jobs` |
| `N8N_USER` / `N8N_PASSWORD` | n8n | `admin` / `admin123` |
| `APIFY_API_TOKEN` | Scraping | `apify_api_xxxx...` |
| `FIRECRAWL_API_KEY` | Scraping | `fc-58ea...` |

---

## 7. Python Environment

### 7.1 AI Job Matcher Dependencies (80 packages)

| Package | Version | Purpose |
|---------|---------|---------|
| `psycopg2-binary` | ≥2.9.9 | PostgreSQL driver |
| `openai` | ≥1.0.0 | OpenAI API client |
| `google-generativeai` | ≥0.3.0 | Google Gemini AI |
| `python-dotenv` | ≥1.0.0 | Environment variable management |
| `google-api-python-client` | ≥2.100.0 | Google Docs/Drive/Sheets |
| `google-auth-oauthlib` | ≥1.1.0 | Google OAuth 2.0 |
| `google-auth-httplib2` | ≥0.1.1 | Google HTTP auth |
| `openpyxl` | ≥3.1.2 | Excel export engine |
| `pandas` | ≥2.0.0 | Data manipulation |
| `streamlit` | ≥1.30.0 | Web dashboard framework |
| `plotly` | ≥5.18.0 | Interactive charts |
| `requests` | ≥2.31.0 | HTTP client (Telegram, LinkedIn) |
| `beautifulsoup4` | ≥4.12.0 | HTML parsing (LinkedIn scraping) |
| `pdfkit` | ≥1.0.0 | PDF generation |

### 7.2 Runtime

| Property | Value |
|----------|-------|
| Python | 3.14+ (`.venv\Scripts\python.exe`) |
| Virtual Env | `AI_Job_Matcher\.venv\` |
| Requirements | `AI_Job_Matcher\requirements.txt` |

---

## 8. Data Flow — Processing Pipeline

```
  ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌────────────┐
  │ 1.INGEST│     │ 2.SCORE  │     │3.QUALIFY │     │4.ENHANCE │     │ 5. OUTPUT  │
  │         │     │          │     │          │     │          │     │            │
  │ LinkedIn│────►│  OpenAI  │────►│  ≥ 75%?  │────►│  OpenAI  │────►│ Google Doc │
  │ fetcher │     │ (1 call) │     │   YES    │     │ (1 call) │     │ custom CV  │
  │ or      │     │          │     │          │     │          │     │            │
  │ Import  │     │ Score    │     │ NO ──►   │     │ Tailored │     │ Telegram   │
  │ utility │     │  [0-100] │     │ low_score│     │ Resume   │     │ Notify     │
  └─────────┘     └──────────┘     └──────────┘     └──────────┘     └────────────┘
                                                                      │
                                                                      ▼
                                                                ┌────────────┐
                                                                │ Streamlit  │
                                                                │ Dashboard  │
                                                                │ :8501      │
                                                                └────────────┘
```

**AI Cost Optimization** (vs legacy n8n pipeline):

| Metric | Before (n8n) | After (Python) | Saving |
|--------|-------------|----------------|--------|
| AI Calls/Job | 18+ | 1–2 | **94%** |
| Tokens/Job | ~60,000 | ~3,500 | **94%** |
| Time/Job | ~90s | ~8s | **91%** |
| Cost/10K Jobs | ~$120 | ~$7 | **94%** |

---

## 9. Access Points Summary

| Service | URL | Credentials |
|---------|-----|-------------|
| **Streamlit Dashboard** | http://localhost:8501 | None (open) |
| **Metabase Analytics** | http://localhost:3000 | Setup on first access |
| **PostgreSQL (host)** | `127.0.0.1:5432` | `job_matcher` / `JobMatcher2024!` |
| **PostgreSQL (Docker internal)** | `job_matcher_postgres:5432` | Same |

---

## 10. Batch Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup.bat` | Full first-time setup | `setup.bat` |
| `start.bat` | Start Docker + services | `start.bat` |
| `stop.bat` | Stop all services | `stop.bat` |
| `process_jobs.bat` | Run batch job processing | `process_jobs.bat` |

---

## 11. TO-BE Architecture (Planned Enhancements)

### 11.1 Planned Changes

| Area | Current (AS-IS) | Target (TO-BE) | Priority |
|------|-----------------|----------------|----------|
| **Port Conflict** | Both stacks use 5432 — cannot coexist | Remap LinkedIn Scrapper to 5433 or unify databases | High |
| **LinkedIn Scrapper** | 5 Docker containers (stopped) | Deprecate or merge scraping into AI Job Matcher | Medium |
| **AI Provider** | OpenAI only (+ Gemini in `multi_ai_analyzer`) | Full multi-AI with cost routing | Medium |
| **Monitoring** | Streamlit only | Add Metabase dashboards for historical analytics | Low |
| **CV Output** | Google Docs only | Google Docs + PDF local + email delivery | Low |
| **Deployment** | Manual `docker compose up` | Automated startup via Windows Task Scheduler | Low |

### 11.2 Target Architecture Diagram

```
┌─────────────────────── msi-laptop (192.168.16.111) ───────────────────────────┐
│                                                                                 │
│  ┌──────────────── Unified Docker Stack ──────────────────────────────────────┐ │
│  │  Network: job_matcher_network (172.20.0.0/16)                              │ │
│  │                                                                            │ │
│  │  ┌─── PostgreSQL ───┐  ┌── Metabase ──┐  ┌─── n8n (optional) ───┐        │ │
│  │  │  :5432            │  │  :3000       │  │  :5678               │        │ │
│  │  │  job_matcher DB   │  │  Analytics   │  │  Workflow fallback   │        │ │
│  │  │  linkedin_jobs DB │  │              │  │                      │        │ │
│  │  └──────────────────-┘  └─────────────┘  └──────────────────────┘        │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌──────────────── Python Services (host) ────────────────────────────────────┐ │
│  │  Streamlit :8501  │  job_matcher.py  │  multi_ai_analyzer.py              │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│                    ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│                    │ OpenAI   │  │ Gemini   │  │ Telegram │                    │
│                    │ + Claude │  │          │  │          │                    │
│                    └──────────┘  └──────────┘  └──────────┘                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key TO-BE changes:**
1. **Unified PostgreSQL** — consolidate `job_matcher` and `linkedin_jobs` into one Postgres instance 
2. **Deprecate LinkedIn Scrapper stack** — merge scraping into `linkedin_job_fetcher.py` 
3. **Multi-AI routing** — add Claude as third provider with cost-based routing
4. **Optional n8n** — keep for webhook triggers only, not for AI processing

---

## 12. Security Considerations

| Secret | Storage | Risk Level | Recommendation |
|--------|---------|------------|----------------|
| `OPENAI_API_KEY` | `.env` file | 🔴 High | Rotate regularly, never commit |
| `DB_PASSWORD` | `.env` file | 🟡 Medium | Change from default |
| `TELEGRAM_BOT_TOKEN` | `.env` file | 🟡 Medium | Restrict bot permissions |
| `APIFY_API_TOKEN` | `.env` file | 🟡 Medium | Rotate if compromised |
| Google OAuth | `credentials.json` | 🔴 High | Keep out of git, use service account |

> [!CAUTION]  
> The `.env` files contain production API keys and database passwords. Ensure `.env` is listed in `.gitignore` and never committed to version control.

---

## 13. Operational Runbook

### Start Everything
```powershell
cd D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher

# 1. Start Docker containers
docker compose -f docker-compose.postgres.yml up -d

# 2. Start Streamlit dashboard
.\.venv\Scripts\streamlit.exe run dashboard.py --server.port 8501
```

### Stop Everything
```powershell
docker compose -f docker-compose.postgres.yml down
# Streamlit: Ctrl+C in its terminal
```

### Process Jobs
```powershell
.\.venv\Scripts\python.exe job_matcher.py
# or with dry run:
.\.venv\Scripts\python.exe job_matcher.py --dry-run
```

### Export to Excel
```powershell
.\.venv\Scripts\python.exe export_to_excel.py --min-score 80
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | DataOps | Initial release |
| 2.0 | 2026-02-10 | DataOps | Complete rewrite: AS-IS/TO-BE, all components, IPs, networks, secrets, LinkedIn Scrapper inventory |
