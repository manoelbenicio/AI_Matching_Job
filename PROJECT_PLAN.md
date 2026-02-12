# AI Job Matcher - Project Plan

> **Project Goal**: Automate LinkedIn job matching and resume customization  
> **Status**: Phase 6 — Feature Complete, Config Remaining  
> **Last Updated**: 2026-02-11 22:37 BRT

---

## 🎯 Project Overview

1. **Fetch LinkedIn jobs** (via URL scraping, Excel import, or manual entry)
2. **AI scores each job** against your CV (0-100 match score via GPT-4o-mini)
3. **Generate custom resumes** for jobs scoring ≥70% (AI CV Enhancement via Gemini 2.0)
4. **Premium ATS export** — B&W DOCX format optimized for Applicant Tracking Systems
5. **Upload to Google Drive** for easy access (auto-archive ≥70%)
6. **Alerts** — Telegram bot + email notifications for high-match jobs
7. **Scheduled batch processing** — cron-based automatic scoring
8. **Track everything** in PostgreSQL + modern Next.js dashboard

---

## ✅ Master Checklist

### Phase 1: Infrastructure Setup ✅
- [x] Set up PostgreSQL database (Docker)
- [x] Create database schema (11 tables)
- [x] Create Python backend (FastAPI)
- [x] Create Next.js frontend (TypeScript)
- [x] Docker Compose for full stack (3 services)
- [x] Create architecture documentation

### Phase 2: Core Dashboard ✅
- [x] Data Table view (TanStack Table, sort/filter/search)
- [x] Kanban Board view (drag-and-drop, swimlanes)
- [x] Split View (table + kanban side-by-side)
- [x] Job Detail Panel (3 tabs: details, CV, audit)
- [x] Command Palette (Ctrl+K fuzzy search)
- [x] Metrics Bar (5 stat cards)
- [x] Dark/Light theme toggle (localStorage persistence)

### Phase 3: AI Pipeline ✅
- [x] AI scoring (GPT-4o-mini, SSE streaming, 5 endpoints)
- [x] CV enhancement (Gemini 2.0, diff view, version history)
- [x] Single-job deep scoring (7-dimension analysis)
- [x] Quick Add URL bar (fetch → score in one click)
- [x] Job scraper (extract from any job URL)

### Phase 4: Polish & Accessibility ✅
- [x] A11y audit pass (ARIA labels, focus management)
- [x] Error boundary with retry
- [x] Toast notification system
- [x] Skeleton loading states
- [x] Keyboard navigation (J/K, Enter/Esc, DnD)

### Phase 5: Sprint LATER Features ✅
- [x] Premium CV Export — ATS-safe B&W DOCX (python-docx)
- [x] Google Drive auto-archive — upload enhanced CVs
- [x] Alerts — Email (SMTP) + Telegram bot notifications
- [x] Scheduler — APScheduler cron batch scoring
- [x] Automated tests — 13 tests (11 pass, 2 skip)
- [x] 3-tab Settings UI (API Keys / Notifications / Scheduler)

### Phase 6: Configuration ← **YOU ARE HERE**
- [x] OpenAI API key configured in `.env`
- [x] Gemini API key configured in `.env`
- [x] Telegram bot token + chat ID configured in `.env`
- [ ] SMTP email credentials (optional)
- [ ] Google Drive OAuth credentials (optional)
- [ ] Enable scheduler (`SCHEDULER_ENABLED=true` in `.env`)

---

## 📊 Current Database Status

| Metric | Value |
|--------|-------|
| Total Jobs | 11,778 |
| Database Tables | 11 |
| API Endpoints | 28 |
| Frontend Components | 20 |
| Backend Files | 14 |

---

## 💻 Key Commands

```powershell
# Start the full stack (Docker)
docker compose up --build

# Start backend (local dev)
cd backend
uvicorn app.main:app --reload --port 8000

# Start frontend (local dev)
cd frontend
npm run dev

# Run tests
cd backend
python -m pytest tests/ -v

# Stop everything
docker compose down
```

---

## 📁 Project Files

### Backend (14 files)

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app + CORS + scheduler lifespan |
| `backend/app/routes/jobs.py` | Job CRUD, stats, URL fetch (5 endpoints) |
| `backend/app/routes/scoring.py` | AI scoring pipeline, SSE streaming (5 endpoints) |
| `backend/app/routes/cv.py` | CV enhance, parse, premium export, Drive archive (5 endpoints) |
| `backend/app/routes/settings.py` | API key management (4 endpoints) |
| `backend/app/routes/candidates.py` | Candidate management (4 endpoints) |
| `backend/app/routes/notifications.py` | Notification prefs + test alerts (4 endpoints) |
| `backend/app/routes/audit.py` | Audit trail (1 endpoint) |
| `backend/app/services/job_scraper.py` | Generic job URL scraper |
| `backend/app/services/premium_export.py` | ATS-optimized B&W DOCX generation |
| `backend/app/services/drive_service.py` | Google Drive upload |
| `backend/app/services/alerts.py` | Telegram bot + SMTP email |
| `backend/app/services/scheduler.py` | APScheduler cron batch scoring |
| `backend/tests/test_new_features.py` | 13 automated tests |

### Frontend (20 components + 6 hooks + 3 lib)

| File | Purpose |
|------|---------|
| `settings-modal.tsx` | 3-tab settings (Keys / Notifications / Scheduler) |
| `cv-tab.tsx` | CV enhancement + Premium Export + Archive to Drive |
| `kanban-board.tsx` | Drag-and-drop Kanban board |
| `scoring-panel.tsx` | Real-time AI scoring panel (SSE) |
| `data-table.tsx` | Main data grid with sort/filter/search |
| `command-palette.tsx` | Ctrl+K command palette |
| `quick-add-bar.tsx` | URL fetch → score bar |

### Config

| File | Purpose |
|------|---------|
| `.env` | All API keys and configuration |
| `.env.example` | Template for first-time setup |
| `docker-compose.yml` | 3-service stack (db + backend + frontend) |
| `requirements.txt` | Python dependencies |
