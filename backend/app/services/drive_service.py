"""
Google Drive Archive Service.

Uploads ATS-optimized DOCX files to a specified Google Drive folder.
Requires a Google service account JSON key file.
"""

import os
from typing import Optional


def _get_drive_service():
    """Build an authenticated Drive v3 service client."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    if not os.path.isfile(creds_path):
        raise FileNotFoundError(
            f"Google service account file not found at '{creds_path}'. "
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
    folder_id = folder_id or os.getenv("RESUME_FOLDER_ID")
    if not folder_id:
        return {"success": False, "message": "RESUME_FOLDER_ID not configured in .env"}

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
