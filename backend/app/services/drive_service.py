"""
Google Drive Archive Service.

Uploads ATS-optimized DOCX files to a specified Google Drive folder.
Requires a Google service account JSON key file.
"""

import os
from typing import Optional


def _read_setting(*keys: str) -> str:
    """Read setting from env first, then app_settings table."""
    for key in keys:
        val = os.getenv(key, "").strip()
        if val:
            return val

    try:
        from ..db import db
        with db() as (conn, cur):
            placeholders = ", ".join(["%s"] * len(keys))
            cur.execute(
                f"SELECT key, value FROM app_settings WHERE key IN ({placeholders})",
                list(keys),
            )
            rows = cur.fetchall()
            by_key = {r["key"]: str(r["value"]).strip() for r in rows if r.get("value")}
            for key in keys:
                if by_key.get(key):
                    return by_key[key]
    except Exception:
        pass
    return ""


def _get_drive_service():
    """Build an authenticated Drive v3 service client."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    env_path = _read_setting("GOOGLE_SERVICE_ACCOUNT_FILE", "google_service_account_file")
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = []
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(backend_root, "credentials.json"))
    candidates.append(os.path.join(os.getcwd(), "credentials.json"))

    creds_path = next((p for p in candidates if p and os.path.isfile(p)), "")
    if not creds_path:
        checked = ", ".join(candidates)
        raise FileNotFoundError(
            "Google service account file not found. "
            f"Checked: {checked}. "
            "Set GOOGLE_SERVICE_ACCOUNT_FILE in .env or place credentials.json in the backend directory."
        )

    scopes = ["https://www.googleapis.com/auth/drive.file"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    return build("drive", "v3", credentials=creds)


def upload_to_drive(
    file_bytes: bytes,
    filename: str,
    folder_id: Optional[str] = None,
    mime_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
) -> dict:
    """Upload a file to Google Drive and return the file metadata.

    Returns { success, drive_url, file_id, filename }.
    """
    folder_id = folder_id or _read_setting(
        "RESUME_FOLDER_ID",
        "GOOGLE_DRIVE_FOLDER_ID",
        "resume_folder_id",
        "google_drive_folder_id",
    )
    if not folder_id:
        return {
            "success": False,
            "message": (
                "Drive folder id not configured. Set RESUME_FOLDER_ID or GOOGLE_DRIVE_FOLDER_ID "
                "(env or app_settings)."
            ),
        }

    try:
        import io
        from googleapiclient.http import MediaIoBaseUpload

        service = _get_drive_service()

        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=True,
        )

        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        return {
            "success": True,
            "file_id": uploaded["id"],
            "drive_url": uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}"),
            "filename": filename,
        }

    except FileNotFoundError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Drive upload failed: {str(e)}"}
