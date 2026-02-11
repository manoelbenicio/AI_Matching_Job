# AI Job Matcher - Project Plan

> **Project Goal**: Automate LinkedIn job matching and resume customization  
> **Status**: Phase 3 - Configuration  
> **Date**: 2026-02-08

---

## 🎯 Project Overview

1. **Fetch LinkedIn jobs** (via n8n or manual import)
2. **AI scores each job** against your CV (0-100 match score)
3. **Generate custom resumes** for jobs scoring ≥75%
4. **Upload to Google Drive** for easy access
5. **Track everything** in PostgreSQL + Metabase dashboard

---

## ✅ Master Checklist

### Phase 1: Infrastructure Setup
- [x] Set up PostgreSQL database (Docker)
- [x] Set up Metabase dashboard (Docker)
- [x] Create database schema (jobs, logs, candidates)
- [x] Create Python job_matcher.py script
- [x] Create export_to_excel.py script
- [x] Create architecture documentation
- [x] Create infrastructure runbook

### Phase 2: Data Migration
- [x] Connect to existing linkedin_jobs_db
- [x] Create migration script
- [x] Migrate 2,057 jobs to new database
- [x] Verify data integrity

### Phase 3: Configuration ← **YOU ARE HERE**
- [x] Configure Metabase connection to database
- [x] Create `.env` file from template
- [x] Configure n8n-exact prompts in job_matcher.py
- [x] Embed resume in job_matcher.py
- [ ] **Add OpenAI API key to `.env`**
- [ ] Configure Google credentials (optional - for Drive upload)

### Phase 4: Testing
- [ ] Run test batch with 5 jobs
- [ ] Verify AI scoring works correctly
- [ ] Review score quality and justifications
- [ ] Test resume generation (if Google configured)

### Phase 5: Production Run
- [ ] Process all 2,019 pending jobs
- [ ] Monitor progress via Metabase
- [ ] Export qualified jobs to Excel
- [ ] Generate custom resumes for qualified jobs

### Phase 6: Day 2 Operations
- [ ] Document operational procedures
- [ ] Set up scheduled processing (optional)
- [ ] Create alerting/monitoring (optional)

---

## 🔑 Current Action Required

**Edit the `.env` file and add your OpenAI API key:**

```
File: D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\.env
Line 12: OPENAI_API_KEY=sk-your-actual-key-here
```

---

## 📊 Current Database Status

| Metric | Value |
|--------|-------|
| Total Jobs | 2,057 |
| Pending (to process) | 2,019 |
| Low Score | 37 |
| Qualified | 1 |

---

## 💻 Key Commands

```powershell
# Check status
python job_matcher.py --stats

# Process jobs (test with 5 first)
python job_matcher.py --batch-size 5

# Process larger batch
python job_matcher.py --batch-size 50

# Export to Excel
python export_to_excel.py

# Start/stop infrastructure
docker-compose -f docker-compose.postgres.yml up -d
docker-compose -f docker-compose.postgres.yml down
```

---

## 📁 Project Files

| File | Purpose |
|------|---------|
| `job_matcher.py` | Main processor - run this |
| `export_to_excel.py` | Export qualified jobs |
| `.env` | Your API keys (edit this!) |
| `docker-compose.postgres.yml` | Docker setup |
| `PROJECT_PLAN.md` | This checklist |
| `INFRASTRUCTURE_RUNBOOK.md` | Container details & IPs |
| `SOLUTION_ARCHITECTURE.md` | Technical documentation |
