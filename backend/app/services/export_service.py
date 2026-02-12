"""
Excel Export Service
====================
Adapted from legacy/scripts/export_to_excel.py
Generates in-memory Excel files for the /jobs/export endpoint.
"""

import io
from datetime import datetime
from typing import Optional, List

import pandas as pd
from ..db import db


def generate_excel_export(
    status: Optional[str] = None,
    min_score: int = 0,
    limit: int = 1000,
    job_ids: Optional[List[int]] = None,
) -> io.BytesIO:
    """
    Generate an Excel file with job data matching the given filters.
    Returns an in-memory BytesIO buffer containing the .xlsx file.
    """
    conditions = []
    params: list = []

    # Filter by specific IDs (selected export)
    if job_ids:
        conditions.append("id = ANY(%s)")
        params.append(job_ids)
    else:
        # Filter by status
        if status and status != "all":
            conditions.append("status = %s")
            params.append(status)

        # Filter by minimum score
        if min_score > 0:
            conditions.append("score >= %s")
            params.append(min_score)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        SELECT
            id,
            job_id,
            job_title,
            company_name,
            score,
            justification,
            status,
            job_url,
            apply_url,
            custom_resume_url,
            location,
            salary_info,
            seniority_level,
            work_type,
            employment_type,
            time_posted,
            created_at,
            updated_at
        FROM jobs
        WHERE {where_clause}
        ORDER BY score DESC NULLS LAST, updated_at DESC
        LIMIT %s
    """
    params.append(limit)

    with db() as (conn, cur):
        cur.execute(query, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

    if not rows:
        # Return empty workbook with headers only
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(rows, columns=columns)

    # Format score as percentage string
    if "score" in df.columns and not df.empty:
        df["score"] = df["score"].apply(
            lambda x: f"{x}%" if pd.notna(x) and x is not None else ""
        )

    # Clean URL columns
    for col in ("job_url", "apply_url", "custom_resume_url"):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if pd.notna(x) and x else "")

    # Format datetime columns
    for col in ("created_at", "updated_at", "time_posted"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) and x else ""
            )

    # Rename columns for display
    df.columns = [col.replace("_", " ").title() for col in df.columns]

    # Write to in-memory buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Jobs Export")

        # Auto-adjust column widths
        worksheet = writer.sheets["Jobs Export"]
        for i, col_name in enumerate(df.columns):
            if df.empty:
                max_len = len(str(col_name)) + 2
            else:
                max_len = max(
                    df[col_name].astype(str).apply(len).max(),
                    len(str(col_name)),
                ) + 2
            # Column letter (supports A-Z, AA-AZ for >26 cols)
            col_letter = _column_letter(i)
            worksheet.column_dimensions[col_letter].width = min(max_len, 50)

    buffer.seek(0)
    return buffer


def _column_letter(index: int) -> str:
    """Convert 0-based column index to Excel column letter (A, B, ..., Z, AA, AB, ...)"""
    result = ""
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result
