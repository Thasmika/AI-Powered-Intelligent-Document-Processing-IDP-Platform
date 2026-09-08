from typing import TypedDict, List, Dict, Any, Optional

class ProcessState(TypedDict):
    """
    Represents the state of a document processing workflow in LangGraph.
    """
    # The temp directory where the big PDF was split into sub-PDFs
    folder_path: str
    pdf_files: List[str]

    # The original big PDF dropped by the scanner (e.g. "data/scanner_input/2026-08-17.pdf")
    source_pdf: Optional[str]

    # Temp split directory — cleaned up after Folder Engine copies files out
    split_docs_dir: Optional[str]

    # Stage 2: Extraction
    qr_payload: Optional[Dict[str, Any]]
    ocr_text: Optional[str]
    ocr_container_no: Optional[str]

    # Stage 3: Validation & Classification
    validation_status: str  # "PENDING", "VALID", "WARNING", "ERROR"
    classified_documents: List[Dict[str, str]]  # e.g., [{"type": "GatePass", "path": "..."}, ...]

    # Stage 4: Storage
    final_folder_path: Optional[str]
    error_message: Optional[str]
