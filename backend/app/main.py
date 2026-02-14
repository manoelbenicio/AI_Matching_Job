"""
AI Job Matcher — FastAPI Backend
Serves the Next.js frontend with data from the existing PostgreSQL database.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from the parent AI_Job_Matcher directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from .routes import jobs, cv, audit, scoring, settings, candidates, notifications  # noqa: E402

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    from .db import get_pool, close_pool  # noqa: E402
    get_pool()  # initialize on startup

    # Start scheduler (if enabled via SCHEDULER_ENABLED=true)
    try:
        from .services.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
    except Exception:
        pass

    yield

    # Shutdown
    try:
        from .services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    close_pool()

app = FastAPI(
    title="AI Job Matcher API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://192.168.16.111:3000",
        "http://192.168.16.111:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(jobs.router, prefix="/api")
app.include_router(cv.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(scoring.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
