from typing import TypedDict, List, Dict, Any, Optional

class ProcessState(TypedDict):
    """
    Represents the state of a document processing workflow in LangGraph.
    """
    file_path: str
    
    # Stage 2: Extraction
    qr_payload: Optional[Dict[str, Any]]
    ocr_text: Optional[str]
    ocr_container_no: Optional[str]
    
    # Stage 3: Validation & Classification
    validation_status: str # "PENDING", "VALID", "WARNING", "ERROR"
    classified_documents: List[Dict[str, str]] # e.g., [{"type": "GatePass", "path": "..."}, ...]
    
    # Stage 4: Storage
    final_folder_path: Optional[str]
    error_message: Optional[str]
