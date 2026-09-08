"""
EFL Global IDP — Warehouse Scanner Watcher
==========================================
This script runs on the WAREHOUSE PC.
It watches for scanned PDFs and uploads them to the cloud server.

The manager only needs to:
  1. Turn on the PC
  2. Scan documents with Kodak scanner
  3. Everything else is automatic!
"""

import time
import os
import sys
import shutil
import requests
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# CONFIGURATION — Change the SERVER_URL to match your hosted system
# ──────────────────────────────────────────────────────────────────

SERVER_URL = "http://130.61.243.161:8003"

# Local folders (relative to this script's location)
SCRIPT_DIR = Path(__file__).resolve().parent
WATCH_DIR = SCRIPT_DIR / "scanner_input"
UPLOADED_DIR = SCRIPT_DIR / "scanner_uploaded"

# Retry settings
RETRY_DELAY = 10  # seconds between retries
# ──────────────────────────────────────────────────────────────────

UPLOAD_URL = f"{SERVER_URL}/api/v1/upload-scanner-pdf"
PING_URL = f"{SERVER_URL}/api/v1/ping"


def check_server():
    """Check if the cloud server is reachable."""
    print(f"  Connecting to {SERVER_URL} ...")
    try:
        r = requests.get(PING_URL, timeout=10)
        if r.status_code == 200:
            print(f"  CONNECTED to EFL Global IDP Server")
            return True
    except Exception:
        pass
    print(f"  WARNING: Cannot reach server. Will keep trying...")
    return False


def upload_file(pdf_path):
    """Upload one PDF to the cloud server. Returns True on success."""
    name = pdf_path.name
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"\n  UPLOADING: {name} ({size_mb:.1f} MB)")

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (name, f, "application/pdf")}
            r = requests.post(
                UPLOAD_URL,
                files=files,
                params={"token": "dummy-jwt-token"},
                timeout=120,
            )
        if r.status_code == 200:
            print(f"  SUCCESS: {name} uploaded and queued for AI processing")
            return True
        elif r.status_code == 409:
            print(f"  SKIPPED: {name} is already being processed")
            return True
        else:
            print(f"  FAILED: Server returned error {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  FAILED: No internet connection. Will retry...")
        return False
    except requests.exceptions.Timeout:
        print(f"  FAILED: Upload timed out. Will retry...")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def upload_with_retry(pdf_path):
    """Keep trying to upload until it succeeds."""
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            print(f"  Retry attempt {attempt} for {pdf_path.name}...")

        if upload_file(pdf_path):
            # Move to backup folder
            try:
                dest = UPLOADED_DIR / pdf_path.name
                shutil.move(str(pdf_path), str(dest))
                print(f"  BACKUP: Moved to scanner_uploaded/")
            except Exception as e:
                print(f"  WARNING: Could not move file: {e}")
            return

        print(f"  Waiting {RETRY_DELAY} seconds before retry...")
        time.sleep(RETRY_DELAY)


def upload_pending_files():
    """Upload any PDFs that are waiting in the scanner_input folder."""
    pdfs = sorted(WATCH_DIR.glob("*.pdf"))
    if pdfs:
        print(f"\n  Found {len(pdfs)} pending PDF(s). Uploading now...")
        for pdf in pdfs:
            upload_with_retry(pdf)
    else:
        print("  No pending PDFs found.")


def watch_folder():
    """Simple polling watcher — checks for new PDFs every 3 seconds."""
    print(f"\n  WATCHING: {WATCH_DIR}")
    print(f"  Scan a document to test the system.\n")
    print("-" * 50)

    known_files = set()
    # Track what's already there
    for f in WATCH_DIR.glob("*.pdf"):
        known_files.add(f.name)

    while True:
        try:
            current_files = set()
            for f in WATCH_DIR.glob("*.pdf"):
                current_files.add(f.name)

            # Find new files
            new_files = current_files - known_files
            for name in sorted(new_files):
                pdf_path = WATCH_DIR / name
                print(f"\n  NEW SCAN DETECTED: {name}")

                # Wait for scanner to finish writing the file
                print("  Waiting 5 seconds for file to complete...")
                time.sleep(5)

                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    upload_with_retry(pdf_path)

            known_files = set()
            for f in WATCH_DIR.glob("*.pdf"):
                known_files.add(f.name)

            time.sleep(3)  # Check every 3 seconds

        except KeyboardInterrupt:
            print("\n\n  Scanner watcher stopped.")
            break
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)


def main():
    # Create folders
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 50)
    print("  EFL Global IDP - Warehouse Scanner")
    print("=" * 50)
    print(f"  Server : {SERVER_URL}")
    print(f"  Watch  : {WATCH_DIR}")
    print(f"  Backup : {UPLOADED_DIR}")
    print("=" * 50)
    print()

    # Check connection
    check_server()

    # Upload any leftover files from yesterday
    upload_pending_files()

    # Start watching for new scans
    watch_folder()


if __name__ == "__main__":
    main()
