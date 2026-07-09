"""
drive_parse_all.py
------------------
Downloads every Excel file from a Google Drive folder and runs the
parse_excel NLP pipeline on each one, saving a separate *_nlp.md file
named after the original JSR file.

Usage:
    python backend/drive_parse_all.py

Configuration:
    Set DRIVE_FOLDER_ID in the .env file (backend/.env) or export it as
    an environment variable before running.

    DRIVE_FOLDER_ID is the long ID string from your Google Drive folder URL:
    https://drive.google.com/drive/folders/<DRIVE_FOLDER_ID>
"""

import os
import io
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# ── Load env from backend/.env ────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Import the core parse logic from parse_excel ──────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from parse_excel import process_excel_fast

# ── Constants ─────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

# Google Drive MIME types for Excel files
EXCEL_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    # Google Sheets can be exported as xlsx too
    "application/vnd.google-apps.spreadsheet": ".xlsx",
}

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE       = Path(__file__).parent / "token.json"
DOWNLOAD_DIR     = Path(__file__).parent / "jsr_downloads"
OUTPUT_DIR       = Path(__file__).parent / "jsr_nlp_outputs"

# ──────────────────────────────────────────────────────────────────────────────

def get_drive_credentials():
    """Get/refresh Google OAuth credentials, reusing token.json if available."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def list_excel_files(service, folder_id: str) -> list[dict]:
    """Return a list of all Excel/Sheets files inside the given Drive folder."""
    mime_query = " or ".join(
        [f"mimeType='{m}'" for m in EXCEL_MIME_TYPES]
    )
    query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"

    files = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def download_file(service, file_id: str, file_name: str, mime_type: str, dest_dir: Path) -> Path:
    """Download a Drive file to dest_dir and return its local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    if mime_type == "application/vnd.google-apps.spreadsheet":
        # Export Google Sheet → xlsx
        ext = ".xlsx"
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        ext = EXCEL_MIME_TYPES.get(mime_type, ".xlsx")
        request = service.files().get_media(fileId=file_id)

    # Ensure file_name ends with the correct extension
    stem = Path(file_name).stem
    local_path = dest_dir / f"{stem}{ext}"

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    local_path.write_bytes(buf.getvalue())
    return local_path


def process_all_from_drive(folder_id: str, mistral_key: str, model_name: str):
    """Main pipeline: list → download → NLP parse → save .md outputs."""
    print(f"\n{'='*60}")
    print(f"  Google Drive → NLP Pipeline")
    print(f"  Folder ID : {folder_id}")
    print(f"  Model     : {model_name}")
    print(f"{'='*60}\n")

    # Auth
    creds   = get_drive_credentials()
    service = build("drive", "v3", credentials=creds)

    # List files
    files = list_excel_files(service, folder_id)
    if not files:
        print("❌  No Excel files found in the specified Drive folder.")
        print("    → Double-check the DRIVE_FOLDER_ID and folder sharing permissions.")
        return

    print(f"✅  Found {len(files)} Excel file(s) in Drive folder:\n")
    for i, f in enumerate(files, 1):
        print(f"   {i}. {f['name']}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, file_info in enumerate(files, 1):
        name      = file_info["name"]
        file_id   = file_info["id"]
        mime_type = file_info["mimeType"]
        stem      = Path(name).stem          # e.g. "pod4jsr" from "pod4jsr.xlsx"

        print(f"\n[{idx}/{len(files)}] Processing: {name}")
        print(f"  ⬇  Downloading from Drive...")

        try:
            local_path = download_file(service, file_id, name, mime_type, DOWNLOAD_DIR)
            print(f"  ✅  Saved to: {local_path}")
        except Exception as e:
            print(f"  ❌  Download failed: {e}")
            results.append({"file": name, "status": "download_failed", "error": str(e)})
            continue

        print(f"  🔍  Running NLP parse pipeline...")
        try:
            result = process_excel_fast(str(local_path), mistral_key, model_name)
        except Exception as e:
            print(f"  ❌  Parse failed: {e}")
            results.append({"file": name, "status": "parse_failed", "error": str(e)})
            continue

        if result is None:
            print(f"  ⚠️  No tables found in {name}, skipping.")
            results.append({"file": name, "status": "no_tables"})
            continue

        # Rename/move the output .md to the OUTPUT_DIR with JSR filename
        raw_output = Path(result["output_path"])          # e.g. jsr_downloads/pod4jsr_fast_parsed.md
        final_output = OUTPUT_DIR / f"{stem}_nlp.md"      # e.g. jsr_nlp_outputs/pod4jsr_nlp.md
        raw_output.rename(final_output)

        print(f"  ✅  NLP file saved: {final_output.name}")
        print(f"      Tokens in: {result['input_tokens']} | out: {result['output_tokens']} | cost: ${result['cost']:.4f}")
        results.append({
            "file": name,
            "status": "success",
            "output": str(final_output),
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "cost": result["cost"],
        })

        # Small pause between API calls
        if idx < len(files):
            print(f"  ⏳  Waiting 3s before next file...")
            time.sleep(3)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    success = [r for r in results if r["status"] == "success"]
    failed  = [r for r in results if r["status"] not in ("success", "no_tables")]

    for r in success:
        print(f"  ✅  {r['file']}  →  {Path(r['output']).name}")
    for r in failed:
        print(f"  ❌  {r['file']}  →  {r['status']}: {r.get('error', '')}")

    total_cost = sum(r.get("cost", 0) for r in results)
    print(f"\n  Total files processed : {len(results)}")
    print(f"  Successful            : {len(success)}")
    print(f"  Failed                : {len(failed)}")
    print(f"  Total API cost        : ${total_cost:.4f}")
    print(f"\n  Output folder: {OUTPUT_DIR.resolve()}")
    print(f"{'='*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "").strip()
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()
    MISTRAL_MODEL   = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")

    if not DRIVE_FOLDER_ID:
        print("❌  DRIVE_FOLDER_ID is not set!")
        print("    Open backend/.env and add:")
        print('    DRIVE_FOLDER_ID="your_folder_id_here"')
        print()
        print("    You can find the folder ID in your Drive URL:")
        print("    https://drive.google.com/drive/folders/<DRIVE_FOLDER_ID>")
        sys.exit(1)

    if not MISTRAL_API_KEY:
        print("❌  MISTRAL_API_KEY is not set in backend/.env")
        sys.exit(1)

    process_all_from_drive(DRIVE_FOLDER_ID, MISTRAL_API_KEY, MISTRAL_MODEL)
