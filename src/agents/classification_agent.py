import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from src.config import settings
from src.agents.state import ProcessState

def classify_document(state: ProcessState) -> ProcessState:
    """
    Stage 3: Classification Agent
    Uses Azure Document Intelligence to classify documents.
    """
    endpoint = settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY

    # If Azure credentials are not set, we might return a dummy classification or an error
    if not endpoint or not key:
        # Fallback for prototype testing if Azure is not configured
        classified_documents = [{"type": "Unknown Document", "path": state["file_path"]}]
        return {**state, "classified_documents": classified_documents}

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    try:
        with open(state["file_path"], "rb") as f:
            poller = document_analysis_client.begin_analyze_document("prebuilt-document", document=f)
            result = poller.result()

        classified_documents = []
        # Basic keyword-based classification for prototype based on extracted text
        full_text = " ".join([page.content for page in result.pages]).lower()
        
        doc_type = "Unknown Document"
        if "invoice" in full_text:
            doc_type = "Invoice"
        elif "packing list" in full_text:
            doc_type = "Packing List"
        elif "customs" in full_text or "declaration" in full_text:
            doc_type = "Customs Document"
        elif "gate pass" in full_text:
            doc_type = "Gate Pass"
        
        classified_documents.append({"type": doc_type, "path": state["file_path"]})

        return {**state, "classified_documents": classified_documents}

    except Exception as e:
        return {**state, "error_message": f"Classification failed: {str(e)}"}
