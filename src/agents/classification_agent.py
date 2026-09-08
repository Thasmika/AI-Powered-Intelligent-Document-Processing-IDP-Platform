import os
import fitz # PyMuPDF
from src.config import settings
from src.agents.state import ProcessState

def classify_document(state: ProcessState) -> ProcessState:
    """
    Stage 3: Classification Agent
    Classifies each PDF document by checking:
      1. Filename (fastest, most reliable for scanner output)
      2. First-page text content (fallback)
    """
    pdf_files = state.get("pdf_files", [])
    classified_documents = []
    
    try:
        for file_path in pdf_files:
            if not file_path.lower().endswith('.pdf'):
                classified_documents.append({"type": "Unknown Document", "path": file_path})
                continue

            filename = os.path.basename(file_path).lower().replace("_", " ").replace("-", " ")

            # --- Step 1: Classify by filename ---
            doc_type = None
            if any(kw in filename for kw in ["gate pass", "gatepass", "gate  pass", "entry pass"]):
                doc_type = "Gate Pass"
            elif "invoice" in filename:
                doc_type = "Invoice"
            elif "packing" in filename and "list" in filename:
                doc_type = "Packing List"
            elif any(kw in filename for kw in ["customs", "declaration", "customs declaration"]):
                doc_type = "Customs Document"
            elif "bill" in filename and "lading" in filename:
                doc_type = "Bill of Lading"
            elif "delivery" in filename and "order" in filename:
                doc_type = "Delivery Order"

            # --- Step 2: Fallback — classify by first-page text ---
            if not doc_type:
                try:
                    doc = fitz.open(file_path)
                    text = doc[0].get_text("text").lower() if len(doc) > 0 else ""
                    doc.close()

                    if "gate pass" in text or "gatepass" in text or ("in gate" in text and "security" in text):
                        doc_type = "Gate Pass"
                    elif "invoice" in text:
                        doc_type = "Invoice"
                    elif "packing list" in text:
                        doc_type = "Packing List"
                    elif "customs" in text or "declaration" in text:
                        doc_type = "Customs Document"
                    elif "bill of lading" in text:
                        doc_type = "Bill of Lading"
                    elif "delivery order" in text:
                        doc_type = "Delivery Order"
                    else:
                        doc_type = "Unknown Document"
                except Exception:
                    doc_type = "Unknown Document"

            classified_documents.append({"type": doc_type, "path": file_path})

        return {**state, "classified_documents": classified_documents}
        
    except Exception as e:
        return {**state, "error_message": f"Classification failed: {str(e)}"}
