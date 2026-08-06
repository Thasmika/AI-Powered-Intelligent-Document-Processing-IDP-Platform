import os
import json
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from src.config import settings
from src.agents.state import ProcessState

def folder_management(state: ProcessState) -> ProcessState:
    """
    Stage 4: Folder Management Agent
    Creates structured document folders: YYYY-MM-DD_Container-[ContainerNumber]_GP-[GatePassID]/
    Saves QR_Metadata.json and linked documents to Azure Blob Storage or local fallback.
    """
    if state.get("error_message"):
        return state

    qr_payload = state.get("qr_payload") or {}
    container_no = qr_payload.get("container_no", "UNKNOWN-CONTAINER")
    gate_pass_no = qr_payload.get("gate_pass_no", "UNKNOWN-GP")
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_Container-{container_no}_GP-{gate_pass_no}"
    
    conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
    
    if not conn_str:
        # Local fallback if Azure Storage is not configured
        local_dir = settings.EFL_DOCUMENTS_DIR / folder_name
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Metadata
        meta_path = local_dir / "QR_Metadata.json"
        with open(meta_path, "w") as f:
            json.dump(qr_payload, f, indent=4)
            
        # Copy classified documents (simulated by returning the final folder path)
        return {**state, "final_folder_path": str(local_dir)}
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client("efl-documents")
        
        if not container_client.exists():
            container_client.create_container()
            
        # Upload metadata
        meta_blob_client = container_client.get_blob_client(f"{folder_name}/QR_Metadata.json")
        meta_blob_client.upload_blob(json.dumps(qr_payload, indent=4), overwrite=True)
        
        # Upload documents
        for i, doc in enumerate(state.get("classified_documents", [])):
            file_path = doc.get("path")
            doc_type = doc.get("type", "Document").replace(" ", "")
            # e.g. 01_GatePass.pdf
            blob_name = f"{folder_name}/{i+1:02d}_{doc_type}.pdf"
            blob_client = container_client.get_blob_client(blob_name)
            
            with open(file_path, "rb") as f:
                blob_client.upload_blob(f, overwrite=True)
                
        return {**state, "final_folder_path": f"azure://efl-documents/{folder_name}"}
        
    except Exception as e:
        return {**state, "error_message": f"Blob storage error: {str(e)}"}
