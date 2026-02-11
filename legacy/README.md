# Legacy Files

This folder contains scripts, workflows, and documentation from the **original AI Job Matcher** (Streamlit + n8n era).

The project has been rewritten as a **FastAPI + Next.js** stack. These files are kept for reference only.

## Structure

```
legacy/
├── scripts/          # Python scripts + .bat files (Streamlit dashboard, batch scoring, etc.)
├── workflows/        # n8n workflow JSON exports
├── docs/             # Superseded markdown documentation
├── requirements.txt  # Python deps for the legacy scripts (includes Streamlit, etc.)
├── generated_cvs/    # Previously generated CV files
└── Jobs_Linkedin_PROD_8_2_2026.xlsx  # Production data export
```

## If You Need Something

- **New stack quick start** → see root `README.md`
- **Current architecture** → `SOLUTION_ARCHITECTURE.md`
- **Current status** → `docs/STATUS_REPORT_360.md`
