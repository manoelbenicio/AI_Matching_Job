# AI Job Matcher

Full-stack job matching pipeline with AI-powered CV enhancement.

| Layer | Tech | Port |
|-------|------|------|
| Frontend | Next.js 16 + TanStack Table + @dnd-kit Kanban | `:3000` |
| Backend | FastAPI + Gemini AI | `:8000` |
| Database | PostgreSQL 16 | `:5432` |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://docker.com/products/docker-desktop) (required)
- [Node.js 20+](https://nodejs.org) (only for local dev outside Docker)
- Python 3.12+ (only for local dev outside Docker)

### One-command launch

```powershell
# Start everything (Postgres + Backend + Frontend)
docker compose up --build -d

# Or use the batch script:
start.bat
```

### URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/health |

### Stop

```powershell
docker compose down        # stop containers
docker compose down -v     # stop + reset database
# Or: stop.bat
```

---

## Local Development (without Docker)

```powershell
# Terminal 1 — Database
docker compose up db -d

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

> When running outside Docker, set `DB_HOST=127.0.0.1` in your `.env`.
> Inside Docker, the backend connects to `db` (the container hostname).

---

## Environment Variables

Copy `.env.example` → `.env` and fill in your keys:

```powershell
copy .env.example .env
```

Key variables:

| Variable | Purpose | Docker | Local Dev |
|----------|---------|--------|-----------|
| `DB_HOST` | PostgreSQL host | `db` | `127.0.0.1` |
| `GEMINI_API_KEY` | Gemini AI for CV enhancement | required | required |
| `DATABASE_URL` | Full connection string | auto-set in `docker-compose.yml` | set in `.env` |

---

## Project Structure

```
AI_Job_Matcher/
├── backend/           # FastAPI application
│   ├── routes/        # API endpoints (jobs, cv, audit)
│   ├── main.py        # App entry point
│   └── Dockerfile
├── frontend/          # Next.js application
│   ├── src/components/  # React components
│   ├── src/app/       # App router pages
│   └── Dockerfile
├── migrations/        # SQL schema migrations
├── docs/              # Current documentation
│   ├── STATUS_REPORT_360.md
│   └── OPERATIONS_GUIDE.md
├── docker-compose.yml # Full stack (db + backend + frontend)
├── legacy/            # Old Streamlit/n8n scripts (archived)
├── start.bat          # Quick start (Docker)
└── stop.bat           # Quick stop (Docker)
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [SOLUTION_ARCHITECTURE.md](SOLUTION_ARCHITECTURE.md) | System architecture |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | Sprint roadmap |
| [STATUS_REPORT_360.md](docs/STATUS_REPORT_360.md) | Audited status report |
| [OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md) | Operations runbook |
| [OPUS46_HANDOFF.md](docs/OPUS46_HANDOFF.md) | Central status + RCA log for Opus 4.6 handoff |
| [OPUS46_ARCHITECTURE_PROMPT_FINAL.md](docs/OPUS46_ARCHITECTURE_PROMPT_FINAL.md) | Final consolidated architecture brief/prompt for Opus 4.6 |
| [FRONTEND_STATUS.md](FRONTEND_STATUS.md) | Frontend component tracking |
