import os
import json
import shutil
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from src.config import settings
from src.agents.state import ProcessState


def folder_management(state: ProcessState) -> ProcessState:
    """
    Stage 4: Folder Management Agent

    Creates the final structured folder named after the Gate Pass ID:
        data/efl_documents/{gate_pass_no}/

    Actions:
    1. Sorts classified documents so Gate Pass is always first (01_GatePass.pdf).
    2. Copies each sub-PDF into the final folder with a sequenced name.
    3. Writes QR_Metadata.json.
    4. Cleans up the temporary split directory (scanner_input/split_docs/{stem}/).
    5. Writes a .processed marker alongside the original scanner PDF so it is
       never re-processed unless a newer version is dropped.
    """
    if state.get("error_message"):
        return state

    qr_payload   = state.get("qr_payload") or {}
    gate_pass_no = qr_payload.get("gate_pass_no", "UNKNOWN-GP")
    folder_name  = gate_pass_no          # folder name = Gate Pass ID

    conn_str = settings.AZURE_STORAGE_CONNECTION_STRING

    # ------------------------------------------------------------------
    # Sort: Gate Pass always first, everything else by index
    # ------------------------------------------------------------------
    classified_docs = list(state.get("classified_documents", []))
    classified_docs.sort(
        key=lambda d: 0 if d.get("type", "").lower() == "gate pass" else 1
    )

    # ------------------------------------------------------------------
    # LOCAL STORAGE (Azure not configured)
    # ------------------------------------------------------------------
    if not conn_str:
        local_dir = settings.EFL_DOCUMENTS_DIR / folder_name
        local_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata
        meta_path = local_dir / "QR_Metadata.json"
        with open(meta_path, "w") as f:
            json.dump(qr_payload, f, indent=4)

        # Copy each classified sub-PDF with a sequenced name
        for i, doc in enumerate(classified_docs):
            file_path = doc.get("path")
            doc_type  = doc.get("type", "Document").replace(" ", "")
            dest_name = f"{i + 1:02d}_{doc_type}.pdf"   # e.g. 01_GatePass.pdf
            dest_path = local_dir / dest_name
            shutil.copy(file_path, dest_path)
            print(f"[FolderEngine] Saved: {dest_name}")

        final_folder_path = str(local_dir)

    # ------------------------------------------------------------------
    # AZURE BLOB STORAGE
    # ------------------------------------------------------------------
    else:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client    = blob_service_client.get_container_client("efl-documents")

            if not container_client.exists():
                container_client.create_container()

            # Upload metadata
            meta_blob = container_client.get_blob_client(f"{folder_name}/QR_Metadata.json")
            meta_blob.upload_blob(json.dumps(qr_payload, indent=4), overwrite=True)

            # Upload each sub-PDF
            for i, doc in enumerate(classified_docs):
                file_path = doc.get("path")
                doc_type  = doc.get("type", "Document").replace(" ", "")
                blob_name = f"{folder_name}/{i + 1:02d}_{doc_type}.pdf"
                blob_client = container_client.get_blob_client(blob_name)
                with open(file_path, "rb") as f:
                    blob_client.upload_blob(f, overwrite=True)

            final_folder_path = f"azure://efl-documents/{folder_name}"

        except Exception as e:
            return {**state, "error_message": f"Blob storage error: {str(e)}"}

    # ------------------------------------------------------------------
    # Clean up temp split directory
    # ------------------------------------------------------------------
    split_docs_dir = state.get("split_docs_dir")
    if split_docs_dir and os.path.isdir(split_docs_dir):
        try:
            shutil.rmtree(split_docs_dir)
            print(f"[FolderEngine] Cleaned up temp split dir: {split_docs_dir}")
        except Exception as e:
            print(f"[FolderEngine] Warning: could not remove temp dir '{split_docs_dir}': {e}")

    # ------------------------------------------------------------------
    # Delete the original scanner PDF to save storage space
    # ------------------------------------------------------------------
    source_pdf = state.get("source_pdf")
    if source_pdf and os.path.exists(source_pdf):
        try:
            os.remove(source_pdf)
            print(f"[FolderEngine] Deleted original scanner PDF: {source_pdf}")
        except Exception as e:
            print(f"[FolderEngine] Warning: could not delete original PDF '{source_pdf}': {e}")

    safe_path = final_folder_path.encode("ascii", errors="replace").decode("ascii")
    print(f"[FolderEngine] [OK] Folder ready: {safe_path}")
    return {**state, "final_folder_path": final_folder_path}
