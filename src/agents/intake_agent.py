import os
from pathlib import Path
from src.config import settings
from src.agents.state import ProcessState

def simulate_intake_process(file_path: Path) -> ProcessState:
    """
    Stage 1: Intake Agent
    Monitors scanner output folders and batches new PDFs.
    For this prototype, it takes a file path and initializes the ProcessState.
    """
    if not file_path.exists():
        return {
            "file_path": str(file_path),
            "qr_payload": None,
            "ocr_text": None,
            "ocr_container_no": None,
            "validation_status": "ERROR",
            "classified_documents": [],
            "final_folder_path": None,
            "error_message": "File not found"
        }
        
    return {
        "file_path": str(file_path),
        "qr_payload": None,
        "ocr_text": None,
        "ocr_container_no": None,
        "validation_status": "PENDING",
        "classified_documents": [],
        "final_folder_path": None,
        "error_message": None
    }

def get_new_scanned_files():
    """
    Yields paths to PDF files in the scanner input directory.
    """
    for file in settings.SCANNER_INPUT_DIR.glob("*.pdf"):
        yield file
