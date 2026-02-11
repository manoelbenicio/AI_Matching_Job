# AI Job Matcher - Infrastructure Runbook

> **Last Updated**: 2026-02-08  
> **Environment**: Development/Local (Docker)  
> **Version**: 1.0

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOST MACHINE (Windows)                      │
│                     IP: localhost / 127.0.0.1                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Docker Network: job_matcher_network         │   │
│  │                    Subnet: 172.20.0.0/16                 │   │
│  │                                                          │   │
│  │  ┌──────────────────────┐  ┌──────────────────────────┐ │   │
│  │  │   PostgreSQL 15      │  │     Metabase v0.48       │ │   │
│  │  │   job_matcher_postgres│  │   job_matcher_metabase   │ │   │
│  │  │   IP: 172.20.0.2     │  │   IP: 172.20.0.3         │ │   │
│  │  │   Port: 5432         │  │   Port: 3000             │ │   │
│  │  └──────────────────────┘  └──────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Python Application (Host)                   │   │
│  │         job_matcher.py → Connects to PostgreSQL         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Container Inventory

| Container Name | Image | Internal IP | Host Port | Internal Port | Purpose |
|----------------|-------|-------------|-----------|---------------|---------|
| `job_matcher_postgres` | `postgres:15-alpine` | 172.20.0.2 | **5432** | 5432 | Primary database for job data |
| `job_matcher_metabase` | `metabase/metabase:v0.48.0` | 172.20.0.3 | **3000** | 3000 | Business intelligence dashboard |
| `n8n-jobs` | `n8nio/n8n:latest` | N/A | **5678** | 5678 | Original workflow automation (legacy) |
| `linkedin_jobs_db` | `postgres:16-alpine` | N/A | **5433** | 5432 | Legacy LinkedIn jobs database |

---

## 🔌 Connection Details

### PostgreSQL - Job Matcher Database

| Property | Value |
|----------|-------|
| **Container Name** | `job_matcher_postgres` |
| **Docker Network** | `job_matcher_network` |
| **Internal IP** | `172.20.0.2` |
| **Host Access** | `localhost:5432` |
| **Database Name** | `job_matcher` |
| **Username** | `job_matcher` |
| **Password** | `JobMatcher2024!` |
| **Connection String (Host)** | `postgresql://job_matcher:JobMatcher2024!@localhost:5432/job_matcher` |
| **Connection String (Docker)** | `postgresql://job_matcher:JobMatcher2024!@job_matcher_postgres:5432/job_matcher` |

### Metabase Dashboard

| Property | Value |
|----------|-------|
| **Container Name** | `job_matcher_metabase` |
| **Docker Network** | `job_matcher_network` |
| **Internal IP** | `172.20.0.3` |
| **URL** | http://localhost:3000 |
| **Data Directory** | Docker Volume: `ai_job_matcher_metabase_data` |

---

## 🗂️ Docker Volumes

| Volume Name | Purpose | Mount Point |
|-------------|---------|-------------|
| `ai_job_matcher_postgres_data` | PostgreSQL data persistence | `/var/lib/postgresql/data` |
| `ai_job_matcher_metabase_data` | Metabase configuration & state | `/metabase.db` |

---

## 📁 File Structure

```
D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\
│
├── 📄 docker-compose.postgres.yml    # Docker Compose configuration
├── 📄 job_matcher.py                 # Main Python processor
├── 📄 export_to_excel.py             # Excel export utility
├── 📄 import_sheets_to_postgres.py   # Google Sheets migration
├── 📄 requirements.txt               # Python dependencies
├── 📄 .env.example                   # Environment template
├── 📄 QUICK_START.md                 # Quick start guide
├── 📄 INFRASTRUCTURE_RUNBOOK.md      # This document
│
└── 📁 migrations/
    └── 📄 001_initial_schema.sql     # Database schema
```

---

## 🔧 Operations Commands

### Start Infrastructure
```powershell
cd D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher
docker-compose -f docker-compose.postgres.yml up -d
```

### Stop Infrastructure
```powershell
docker-compose -f docker-compose.postgres.yml down
```

### View Container Logs
```powershell
# PostgreSQL logs
docker logs job_matcher_postgres -f --tail 100

# Metabase logs
docker logs job_matcher_metabase -f --tail 100
```

### Connect to PostgreSQL (psql)
```powershell
docker exec -it job_matcher_postgres psql -U job_matcher -d job_matcher
```

### Check Container Health
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Restart Services
```powershell
docker-compose -f docker-compose.postgres.yml restart
```

---

## 🗄️ Database Schema

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `jobs` | Main job postings data | `id`, `job_id`, `score`, `status`, `custom_resume_url` |
| `processing_logs` | Batch processing history | `batch_id`, `event_type`, `details` |

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting AI scoring |
| `processing` | Currently being processed |
| `qualified` | Score ≥ 75%, awaiting resume |
| `enhanced` | Resume generated |
| `low_score` | Score < 75% |
| `error` | Processing failed |

### Views (for Metabase)

| View | Purpose |
|------|---------|
| `daily_processing_summary` | Daily stats by status |
| `company_qualified_ranking` | Top companies by qualified jobs |
| `score_distribution` | Score distribution buckets |

---

## 🔐 Security Notes

> ⚠️ **For Production Deployment**

1. **Change Default Passwords**: Update `JobMatcher2024!` to a strong password
2. **Use Environment Variables**: Store secrets in `.env` file (not in docker-compose)
3. **Network Isolation**: Consider removing port bindings and using internal networks
4. **Backup Strategy**: Implement regular PostgreSQL backups

---

## 🆘 Troubleshooting

### Container Won't Start
```powershell
# Check for port conflicts
netstat -an | findstr "5432"
netstat -an | findstr "3000"

# Remove and recreate
docker-compose -f docker-compose.postgres.yml down -v
docker-compose -f docker-compose.postgres.yml up -d
```

### Database Connection Failed
```powershell
# Verify PostgreSQL is healthy
docker inspect job_matcher_postgres --format "{{.State.Health.Status}}"

# Check logs for errors
docker logs job_matcher_postgres --tail 50
```

### Reset Everything
```powershell
docker-compose -f docker-compose.postgres.yml down -v
docker volume rm ai_job_matcher_postgres_data ai_job_matcher_metabase_data
docker-compose -f docker-compose.postgres.yml up -d
```

---

## 📞 Quick Reference Card

| Service | URL / Connection |
|---------|------------------|
| **PostgreSQL** | `localhost:5432` |
| **Metabase** | http://localhost:3000 |
| **n8n (legacy)** | http://localhost:5678 |

| Action | Command |
|--------|---------|
| Start | `docker-compose -f docker-compose.postgres.yml up -d` |
| Stop | `docker-compose -f docker-compose.postgres.yml down` |
| Logs | `docker logs <container_name> -f` |
| Shell | `docker exec -it job_matcher_postgres bash` |
