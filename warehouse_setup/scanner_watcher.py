"""
EFL Global IDP — Warehouse Scanner Watcher (Remote Upload Edition)
=================================================================
This script runs on the WAREHOUSE PC (the computer connected to the
physical Kodak Alaris scanner).  It watches the local scanner output
folder and uploads new PDFs to the cloud-hosted IDP system over HTTP.

Workflow:
  1. The Kodak scanner creates a PDF in the local watch folder.
  2. This script detects the new file instantly.
  3. It uploads the PDF to the cloud server via HTTP.
  4. The server's AI pipeline processes it automatically.
  5. The dashboard at http://<SERVER_IP>:8003 updates in real-time.
  6. The local PDF is moved to a "uploaded" backup folder.

Reliability:
  - If the upload fails (internet issue), the script retries
    automatically every 10 seconds until it succeeds.
  - When the warehouse PC shuts down at night and turns back on
    in the morning, the script re-scans the folder and uploads
    any files that were missed.
  - Already-uploaded files (moved to the backup folder) are never
    re-uploaded.

Usage:
  python scripts/scanner_watcher.py

Configuration:
  Edit the SERVER_URL and WATCH_DIR variables below, or set them
  as environment variables.
"""

import time
import os
import sys
import shutil
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ──────────────────────────────────────────────────────────────────────
# CONFIGURATION — Edit these for your warehouse setup
# ──────────────────────────────────────────────────────────────────────

# The URL of your hosted IDP system (change IP/port if different)
SERVER_URL = os.getenv(
    "IDP_SERVER_URL",
    "http://130.61.243.161:8003"
)

# The local folder where the Kodak scanner saves PDFs
# Default: data/scanner_input relative to project root
WATCH_DIR = os.getenv(
    "IDP_WATCH_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'scanner_input'))
)

# Backup folder for successfully uploaded PDFs
UPLOADED_DIR = os.getenv(
    "IDP_UPLOADED_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'scanner_uploaded'))
)

# How many seconds to wait before retrying a failed upload
RETRY_DELAY = 10

# Max retries per file before giving up (0 = infinite)
MAX_RETRIES = 0  # Keep trying forever

# ──────────────────────────────────────────────────────────────────────

UPLOAD_ENDPOINT = f"{SERVER_URL}/api/v1/upload-scanner-pdf"
PING_ENDPOINT = f"{SERVER_URL}/api/v1/ping"


def check_server_connection():
    """Verify the cloud server is reachable before starting."""
    print(f"[Watcher] Checking connection to {SERVER_URL} ...")
    try:
        res = requests.get(PING_ENDPOINT, timeout=10)
        if res.status_code == 200:
            data = res.json()
            print(f"[Watcher] ✅ Connected to {data.get('server', 'IDP Server')} v{data.get('version', '?')}")
            return True
        else:
            print(f"[Watcher] ⚠️  Server responded with status {res.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[Watcher] ❌ Cannot reach server at {SERVER_URL}")
        print(f"[Watcher]    Check your internet connection and server URL.")
        return False
    except Exception as e:
        print(f"[Watcher] ❌ Connection error: {e}")
        return False


def upload_pdf(pdf_path: Path) -> bool:
    """
    Upload a single PDF file to the cloud server.
    Returns True on success, False on failure.
    """
    file_name = pdf_path.name
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)

    print(f"\n[Upload] 📤 Uploading '{file_name}' ({file_size_mb:.1f} MB) ...")

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (file_name, f, "application/pdf")}
            params = {"token": "dummy-jwt-token"}
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                params=params,
                timeout=120,  # 2 min timeout for large files
            )

        if response.status_code == 200:
            result = response.json()
            print(f"[Upload] ✅ Success: {result.get('message', 'OK')}")
            return True
        elif response.status_code == 409:
            print(f"[Upload] ⏳ File is already being processed. Skipping.")
            return True  # Don't retry — it's already in the pipeline
        else:
            print(f"[Upload] ❌ Server error (HTTP {response.status_code}): {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"[Upload] ❌ Cannot connect to server. Will retry...")
        return False
    except requests.exceptions.Timeout:
        print(f"[Upload] ❌ Upload timed out. Will retry...")
        return False
    except Exception as e:
        print(f"[Upload] ❌ Unexpected error: {e}")
        return False


def upload_with_retry(pdf_path: Path):
    """Upload a PDF with automatic retry on failure."""
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            print(f"[Retry] Attempt {attempt} for '{pdf_path.name}' ...")

        success = upload_pdf(pdf_path)

        if success:
            # Move to backup folder
            try:
                uploaded_dir = Path(UPLOADED_DIR)
                uploaded_dir.mkdir(parents=True, exist_ok=True)
                dest = uploaded_dir / pdf_path.name
                shutil.move(str(pdf_path), str(dest))
                print(f"[Backup] 📦 Moved to: {dest}")
            except Exception as e:
                print(f"[Backup] ⚠️  Could not move file: {e}")
            return

        if MAX_RETRIES > 0 and attempt >= MAX_RETRIES:
            print(f"[Retry] ❌ Max retries ({MAX_RETRIES}) reached for '{pdf_path.name}'. Giving up.")
            return

        print(f"[Retry] Waiting {RETRY_DELAY}s before next attempt...")
        time.sleep(RETRY_DELAY)


def scan_existing_files():
    """
    On startup, check for any PDFs that haven't been uploaded yet.
    This handles the case where the PC was shut down before uploads
    completed, or new files arrived while the script wasn't running.
    """
    watch_path = Path(WATCH_DIR)
    pdf_files = sorted(watch_path.glob("*.pdf"))

    if not pdf_files:
        print("[Startup] No pending PDFs found in watch folder.")
        return

    print(f"[Startup] Found {len(pdf_files)} pending PDF(s). Uploading...")
    for pdf_path in pdf_files:
        upload_with_retry(pdf_path)


class ScannerEventHandler(FileSystemEventHandler):
    """Watches for new PDF files created by the Kodak scanner."""

    def on_created(self, event):
        # Ignore directories and non-PDF files
        if event.is_directory:
            return

        # Ignore the split_docs temporary folder
        if "split_docs" in event.src_path:
            return

        if not event.src_path.lower().endswith(".pdf"):
            return

        file_path = Path(event.src_path)
        print(f"\n[Scanner] 🔔 New scan detected: {file_path.name}")

        # Wait for the scanner to finish writing the file
        print("[Scanner] Waiting 5 seconds for file write to complete...")
        time.sleep(5)

        # Verify the file still exists and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            print("[Scanner] ⚠️  File is empty or was removed. Skipping.")
            return

        # Upload to cloud
        upload_with_retry(file_path)


def start_watcher():
    """Main entry point — starts the file watcher."""
    watch_path = Path(WATCH_DIR)
    watch_path.mkdir(parents=True, exist_ok=True)

    uploaded_path = Path(UPLOADED_DIR)
    uploaded_path.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  EFL Global IDP — Warehouse Scanner Watcher")
    print("=" * 60)
    print(f"  Server  : {SERVER_URL}")
    print(f"  Watch   : {WATCH_DIR}")
    print(f"  Backup  : {UPLOADED_DIR}")
    print("=" * 60)
    print()

    # Step 1: Verify server connection
    if not check_server_connection():
        print("\n[Watcher] ⚠️  Server not reachable, but starting anyway.")
        print("[Watcher]    Uploads will retry automatically when connection is restored.\n")

    # Step 2: Upload any files that were left from before (PC was off)
    scan_existing_files()

    # Step 3: Start watching for new files in real-time
    event_handler = ScannerEventHandler()
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=False)

    print(f"\n[Watcher] 👁️  Now watching for new scanned PDFs...")
    print(f"[Watcher]    Scan a document to test the system.\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Watcher] Stopping...")
        observer.stop()
    observer.join()
    print("[Watcher] Stopped.")


if __name__ == "__main__":
    start_watcher()
