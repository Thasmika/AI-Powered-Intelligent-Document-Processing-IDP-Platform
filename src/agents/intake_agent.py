import os
from pathlib import Path
from src.config import settings
from src.agents.state import ProcessState


def simulate_intake_process(pdf_path: Path) -> ProcessState:
    """
    Stage 1: Intake Agent
    Accepts a single big scanner PDF file and initialises the workflow state.
    The pdf_files list is intentionally empty here — the Splitter Agent will
    populate it after it splits the big PDF into individual sub-documents.
    """
    if not pdf_path.exists():
        return {
            "folder_path": str(pdf_path.parent),
            "pdf_files": [],
            "source_pdf": str(pdf_path),
            "split_docs_dir": None,
            "qr_payload": None,
            "ocr_text": None,
            "ocr_container_no": None,
            "validation_status": "ERROR",
            "classified_documents": [],
            "final_folder_path": None,
            "error_message": f"Scanner PDF not found: {pdf_path.name}",
        }

    return {
        "folder_path": str(pdf_path.parent),
        "pdf_files": [],           # will be filled by splitter
        "source_pdf": str(pdf_path),
        "split_docs_dir": None,    # will be filled by splitter
        "qr_payload": None,
        "ocr_text": None,
        "ocr_container_no": None,
        "validation_status": "PENDING",
        "classified_documents": [],
        "final_folder_path": None,
        "error_message": None,
    }


def get_new_scanned_pdfs():
    """
    Yields Path objects for every NEW PDF file found directly inside
    scanner_input/ that has not yet been processed.

    Marker files sit alongside each PDF:
      - {stem}.processing  → job is actively running   → always skip
      - {stem}.processed   → job finished previously   → skip UNLESS a
                             newer PDF (same name) has appeared since the
                             marker was written (handles re-drops).
    """
    scanner_dir = settings.SCANNER_INPUT_DIR

    for item in scanner_dir.iterdir():
        # We only care about PDF files at the top level
        if not item.is_file() or item.suffix.lower() != ".pdf":
            continue

        stem = item.stem
        processing_marker = scanner_dir / f"{stem}.processing"
        processed_marker  = scanner_dir / f"{stem}.processed"

        # Actively being processed → skip unconditionally
        if processing_marker.exists():
            continue

        # Previously processed → check if the PDF has been replaced/updated
        if processed_marker.exists():
            try:
                marker_mtime = processed_marker.stat().st_mtime
                pdf_mtime    = item.stat().st_mtime
                if pdf_mtime > marker_mtime:
                    # A newer/replaced PDF was dropped → re-queue
                    processed_marker.unlink()
                    print(
                        f"[Intake] Updated PDF detected: '{item.name}'. "
                        "Removed .processed marker — re-queuing."
                    )
                else:
                    continue  # Nothing new
            except Exception as e:
                print(f"[Intake] Could not inspect '{item.name}': {e}")
                continue

        yield item
