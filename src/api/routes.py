from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from src.agents.graph import app as workflow_app
from src.agents.intake_agent import get_new_scanned_pdfs, simulate_intake_process
import time
import asyncio
import json
import uuid

router = APIRouter()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Dummy authentication dependency
def verify_token(token: str = "dummy-jwt-token"):
    if token != "dummy-jwt-token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True

class DocumentResponse(BaseModel):
    id: str
    container_no: str
    gate_pass_no: str
    status: str
    folder_path: Optional[str] = None
    error_message: Optional[str] = None
    source_folder: Optional[str] = None
    destination_location: Optional[str] = None

from src.config import settings
from src.database.session import SessionLocal
from src.database.models import DocumentProcess
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Persistence helpers – read/write the SQLite database
# ---------------------------------------------------------------------------

def _db_upsert_document(doc_data: dict):
    """Insert or update a document record in the SQLite database."""
    db = SessionLocal()
    try:
        folder_path = doc_data.get("folder_path")
        existing = None

        # Look up by folder_path first (most stable unique key)
        if folder_path:
            existing = db.query(DocumentProcess).filter(
                DocumentProcess.folder_path == folder_path
            ).first()

        # Fallback: look up by id
        if existing is None:
            existing = db.query(DocumentProcess).filter(
                DocumentProcess.id == doc_data.get("id")
            ).first()

        # Build extracted_data preserving any existing values
        existing_extracted = (existing.extracted_data or {}) if existing else {}
        new_extracted = {**existing_extracted}
        if doc_data.get("source_folder"):
            new_extracted["source_folder"] = doc_data["source_folder"]
        if doc_data.get("destination_location"):
            new_extracted["destination_location"] = doc_data["destination_location"]

        if existing:
            existing.container_no = doc_data.get("container_no", existing.container_no)
            existing.gate_pass_no = doc_data.get("gate_pass_no", existing.gate_pass_no)
            existing.status = doc_data.get("status", existing.status)
            existing.folder_path = folder_path
            existing.error_message = doc_data.get("error_message")
            existing.extracted_data = new_extracted
        else:
            record = DocumentProcess(
                id=doc_data.get("id", "Unknown"),
                container_no=doc_data.get("container_no", "Unknown"),
                gate_pass_no=doc_data.get("gate_pass_no", "Unknown"),
                status=doc_data.get("status", "UNKNOWN"),
                folder_path=folder_path,
                error_message=doc_data.get("error_message"),
                extracted_data=new_extracted,
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Error saving document: {e}")
    finally:
        db.close()


def _db_get_all_documents() -> List[dict]:
    """Return all document records from the SQLite database as dicts."""
    db = SessionLocal()
    try:
        records = db.query(DocumentProcess).order_by(DocumentProcess.created_at).all()
        return [
            {
                "id": r.id,
                "container_no": r.container_no or "Unknown",
                "gate_pass_no": r.gate_pass_no or "Unknown",
                "status": r.status or "UNKNOWN",
                "folder_path": r.folder_path,
                "error_message": r.error_message,
                # The scanner-created folder name (e.g. "2026-08-17")
                "source_folder": (r.extracted_data or {}).get("source_folder"),
                "destination_location": (r.extracted_data or {}).get("destination_location", "Unknown"),
            }
            for r in records
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Startup recovery: scan efl_documents on disk and seed the DB for any
# folders that are already there but not yet recorded (e.g. after a wipe).
# ---------------------------------------------------------------------------

def restore_documents_from_disk():
    """
    Walk the EFL_DOCUMENTS_DIR. For every sub-folder found, check if it
    already exists in the database; if not, create a record from the
    QR_Metadata.json (if present) or fall back to folder-name heuristics.
    """
    efl_dir = settings.EFL_DOCUMENTS_DIR
    if not efl_dir.exists():
        return

    db = SessionLocal()
    try:
        for folder in efl_dir.iterdir():
            if not folder.is_dir():
                continue

            folder_path_str = str(folder)

            # Skip if already in DB — but back-fill source_folder if it was never stored
            existing = db.query(DocumentProcess).filter(
                DocumentProcess.folder_path == folder_path_str
            ).first()
            if existing:
                existing_extracted = existing.extracted_data or {}
                if not existing_extracted.get("source_folder"):
                    # Derive from the record's own id (folder.name was used as id at creation time)
                    existing_extracted["source_folder"] = existing.id or folder.name
                    existing.extracted_data = existing_extracted
                continue

            # Try to read QR_Metadata.json
            meta_file = folder / "QR_Metadata.json"
            gate_pass_no = folder.name  # folder name is gate pass number by convention
            container_no = "Unknown"

            if meta_file.exists():
                try:
                    with open(meta_file, "r") as f:
                        meta = json.load(f)
                    gate_pass_no = meta.get("gate_pass_no", gate_pass_no)
                    container_no = meta.get("container_no", container_no)
                except Exception:
                    pass

            # Determine status from files on disk
            pdf_files = list(folder.glob("*.pdf"))
            if any("GatePass" in f.name for f in pdf_files):
                recovered_status = "VALID"
            elif pdf_files:
                recovered_status = "WARNING"
            else:
                recovered_status = "UNKNOWN"

            record = DocumentProcess(
                id=folder.name,
                container_no=container_no,
                gate_pass_no=gate_pass_no,
                status=recovered_status,
                folder_path=folder_path_str,
                error_message=None,
                # Expose the scanner's date-folder name so the dashboard ID column shows it
                extracted_data={"source_folder": folder.name},
            )
            db.add(record)
            print(f"[DB] Recovered document from disk: {folder.name}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Error during disk recovery: {e}")
    finally:
        db.close()


def cleanup_stale_processing_markers():
    """
    On startup, remove any {stem}.processing marker files that were left behind
    by a previous crash.  A PDF with a .processing marker but no .processed
    marker means the job never finished — clear the marker so it is retried.
    """
    scanner_dir = settings.SCANNER_INPUT_DIR
    if not scanner_dir.exists():
        return
    for item in scanner_dir.iterdir():
        if not item.is_file() or item.suffix.lower() != ".processing":
            continue
        stem = item.stem  # e.g. "2026-08-17 (1)"
        processed_marker = scanner_dir / f"{stem}.processed"
        if not processed_marker.exists():
            try:
                item.unlink()
                print(f"[Startup] Removed stale .processing marker: {item.name}")
            except Exception as e:
                print(f"[Startup] Could not remove stale marker '{item.name}': {e}")


# Run startup routines on import (= server startup)
cleanup_stale_processing_markers()
restore_documents_from_disk()


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

def process_background_pdf(pdf_path: Path):
    """
    Background job: processes a single large scanner PDF through the full
    LangGraph workflow and persists the result to the SQLite database.

    Marker files live alongside the PDF in scanner_input/:
        {stem}.processing  — written before starting
        {stem}.processed   — written on completion (success or error)
    """
    pdf_path = Path(pdf_path)
    pdf_stem = pdf_path.stem   # e.g. "2026-08-17 (1)"
    scanner_dir = pdf_path.parent
    processing_marker = scanner_dir / f"{pdf_stem}.processing"
    processed_marker  = scanner_dir / f"{pdf_stem}.processed"

    try:
        state        = simulate_intake_process(pdf_path)
        result_state = workflow_app.invoke(state)

        qr = result_state.get("qr_payload") or {}
        doc_data = {
            "id":            qr.get("gate_pass_no", pdf_stem),
            "container_no":  qr.get("container_no", "Unknown"),
            "gate_pass_no":  qr.get("gate_pass_no", "Unknown"),
            "status":        result_state.get("validation_status", "UNKNOWN"),
            "folder_path":   result_state.get("final_folder_path"),
            "error_message": result_state.get("error_message"),
            "source_folder": pdf_stem,   # original scanner PDF stem shown in dashboard
            "destination_location": qr.get("destination_location", "Unknown"),
        }
        _db_upsert_document(doc_data)
        print(f"[Background] OK: Processed '{pdf_path.name}' -> folder: {doc_data['folder_path']}")

    except Exception as exc:
        doc_data = {
            "id":            pdf_stem,
            "container_no": "Unknown",
            "gate_pass_no": "Unknown",
            "status":       "ERROR",
            "folder_path":  None,
            "error_message": f"Workflow crashed: {exc}",
            "source_folder": pdf_stem,
        }
        _db_upsert_document(doc_data)
        print(f"[ERROR] Workflow crashed for '{pdf_path.name}': {exc}")

    finally:
        # Remove .processing marker
        if processing_marker.exists():
            try:
                processing_marker.unlink()
            except Exception as e:
                print(f"Warning: Could not remove .processing marker: {e}")

        # Write .processed marker as a safety net ONLY if the file wasn't deleted by folder_engine
        if pdf_path.exists() and not processed_marker.exists():
            try:
                processed_marker.write_text("processed")
                print(f"[Marker] Wrote .processed for: {pdf_path.name}")
            except Exception as e:
                print(f"Warning: Could not write .processed marker: {e}")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@router.post("/trigger-ingestion", dependencies=[Depends(verify_token)])
def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Detects new scanner PDF files in scanner_input/ and queues each one
    for processing through the full LangGraph workflow.

    The scanner drops ONE big PDF per container.  The workflow will:
      1. Split it into individual sub-documents.
      2. Extract the Gate Pass ID.
      3. Create a named folder: efl_documents/{gate_pass_no}/
      4. Save each document separately inside that folder.
    """
    new_pdfs = list(get_new_scanned_pdfs())

    for pdf_path in new_pdfs:
        stem = pdf_path.stem
        processing_marker = pdf_path.parent / f"{stem}.processing"
        try:
            processing_marker.touch()
        except Exception as e:
            print(f"Warning: Could not mark '{pdf_path.name}' as processing: {e}")

        background_tasks.add_task(process_background_pdf, pdf_path)

    return {
        "message": f"Started processing {len(new_pdfs)} scanner PDF(s).",
        "pdfs_queued": [p.name for p in new_pdfs],
    }


@router.post("/upload-scanner-pdf", dependencies=[Depends(verify_token)])
async def upload_scanner_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Receives a PDF file upload from the warehouse scanner PC over HTTP.
    Saves it into the server's scanner_input/ directory and immediately
    triggers the AI processing pipeline in the background.

    This endpoint is the bridge between the physical warehouse scanner
    and the cloud-hosted AI system.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    # Save the uploaded file to scanner_input/
    scanner_dir = settings.SCANNER_INPUT_DIR
    scanner_dir.mkdir(parents=True, exist_ok=True)

    dest_path = scanner_dir / file.filename

    # If a file with the same name already exists and was processed, clean up
    stem = Path(file.filename).stem
    processed_marker = scanner_dir / f"{stem}.processed"
    processing_marker = scanner_dir / f"{stem}.processing"

    if processing_marker.exists():
        raise HTTPException(
            status_code=409,
            detail=f"'{file.filename}' is currently being processed. Please wait.",
        )

    # Remove old markers so the file is treated as brand new
    if processed_marker.exists():
        try:
            processed_marker.unlink()
        except Exception:
            pass

    try:
        contents = await file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)
        print(f"[Upload] Saved '{file.filename}' ({len(contents)} bytes) to scanner_input/")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {e}",
        )

    # Mark as processing and queue the AI pipeline
    try:
        processing_marker.touch()
    except Exception as e:
        print(f"Warning: Could not mark '{file.filename}' as processing: {e}")

    background_tasks.add_task(process_background_pdf, dest_path)

    return {
        "message": f"File '{file.filename}' uploaded and queued for AI processing.",
        "filename": file.filename,
        "size_bytes": len(contents),
    }


@router.get("/ping")
def ping():
    """Simple connectivity check for the warehouse scanner script."""
    return {"status": "ok", "server": "EFL Global IDP", "version": settings.VERSION}


@router.post("/scanner-pdfs/{pdf_filename}/reprocess", dependencies=[Depends(verify_token)])
def reprocess_pdf(pdf_filename: str, background_tasks: BackgroundTasks):
    """
    Manually forces a scanner PDF file to be re-processed, even if it was
    previously marked as .processed.  Useful for re-running a failed or
    updated scan.
    """
    pdf_path = settings.SCANNER_INPUT_DIR / pdf_filename
    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"Scanner PDF '{pdf_filename}' not found.")

    stem = pdf_path.stem
    scanner_dir       = pdf_path.parent
    processing_marker = scanner_dir / f"{stem}.processing"
    processed_marker  = scanner_dir / f"{stem}.processed"

    if processing_marker.exists():
        raise HTTPException(
            status_code=409,
            detail=f"'{pdf_filename}' is currently being processed. Please wait."
        )

    # Remove the .processed marker so the file is treated as new
    if processed_marker.exists():
        try:
            processed_marker.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not remove .processed marker: {e}")

    try:
        processing_marker.touch()
    except Exception as e:
        print(f"Warning: Could not mark '{pdf_filename}' as processing: {e}")

    background_tasks.add_task(process_background_pdf, pdf_path)
    return {
        "message": f"'{pdf_filename}' re-queued for processing.",
    }


@router.get("/documents", response_model=List[DocumentResponse], dependencies=[Depends(verify_token)])
def get_documents():
    """
    Returns all processed documents for the Master Data Grid (from SQLite DB).
    """
    return _db_get_all_documents()


@router.delete("/documents/{document_id}", dependencies=[Depends(verify_token)])
def delete_document(document_id: str):
    """
    Deletes a document record from the database and removes its associated folder from disk.
    """
    db = SessionLocal()
    import shutil
    try:
        record = db.query(DocumentProcess).filter(DocumentProcess.id == document_id).first()
        if not record:
            record = db.query(DocumentProcess).filter(DocumentProcess.gate_pass_no == document_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")

        if record.folder_path and os.path.exists(record.folder_path):
            try:
                shutil.rmtree(record.folder_path)
                print(f"[Delete] Removed folder: {record.folder_path}")
            except Exception as e:
                print(f"[Delete] Warning: Could not delete folder {record.folder_path}: {e}")
                
        db.delete(record)
        db.commit()
        return {"message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/documents/exceptions", response_model=List[DocumentResponse], dependencies=[Depends(verify_token)])
def get_exceptions():
    """
    Returns documents that routed to Dead-Letter Queue (DLQ).
    """
    all_docs = _db_get_all_documents()
    return [doc for doc in all_docs if doc["status"] in ["WARNING", "ERROR"]]


@router.get("/documents/{folder_name}/files", dependencies=[Depends(verify_token)])
def list_folder_files(folder_name: str):
    """
    Lists all PDF files in a given processed folder.
    """
    target_dir = settings.EFL_DOCUMENTS_DIR / folder_name
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    files = []
    for f in target_dir.glob("*.pdf"):
        files.append({"name": f.name, "size": f.stat().st_size})

    metadata = {}
    meta_path = target_dir / "QR_Metadata.json"
    if meta_path.exists():
        import json
        try:
            with open(meta_path, "r") as f:
                metadata = json.load(f)
        except Exception:
            pass

    return {"folder": folder_name, "files": files, "metadata": metadata}


@router.get("/documents/{folder_name}/files/{file_name}")
def get_pdf_file(folder_name: str, file_name: str, token: str = "dummy-jwt-token", download: bool = False):
    """
    Serves the actual PDF file.
    - Default (download=false): serves inline so the browser renders it in an iframe/tab.
    - With ?download=true: forces file download with Content-Disposition: attachment.
    Token is passed as query param so iframe src and <a> tags can include it easily.
    """
    verify_token(token)

    file_path = settings.EFL_DOCUMENTS_DIR / folder_name / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import Response
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'

    with open(file_path, "rb") as f:
        content = f.read()

    return Response(content=content, media_type="application/pdf", headers=headers)


class ChatRequest(BaseModel):
    message: str
    report_context: Optional[str] = None

def generate_groq_completion_with_fallback(client, messages, temperature, max_tokens):
    from src.config import settings
    primary_model = settings.LLM_MODEL
    fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "allam-2-7b"]
    
    try:
        return client.chat.completions.create(
            model=primary_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "does not exist" in error_msg or "not found" in error_msg:
            print(f"[LLM WARNING] Primary model '{primary_model}' failed. Trying fallbacks: {fallback_models}")
            for fallback in fallback_models:
                try:
                    return client.chat.completions.create(
                        model=fallback,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                except Exception:
                    continue
        raise e

@router.post("/chat", dependencies=[Depends(verify_token)])
def chat_with_bot(request: ChatRequest):
    from src.config import settings
    from groq import Groq

    if not settings.GROQ_API_KEY:
        return {"response": "Groq API key is not configured. Please add it to your .env file."}

    client = Groq(api_key=settings.GROQ_API_KEY)

    processed_documents = _db_get_all_documents()

    system_prompt = (
        "You are an IDP AI Assistant for EFL Global. Your job is to help users understand the status of their documents and containers. "
        "You have access to the current state of processed documents in the system. Use this information to answer user queries accurately. "
        "Keep your answers concise, helpful, and professional.\n\n"
        "Current System State (Processed Documents):\n"
        f"{json.dumps(processed_documents, indent=2)}"
    )

    if request.report_context:
        system_prompt += (
            "\n\nContext - The user has recently generated the following report. They might ask questions about it:\n"
            f"--- START REPORT ---\n{request.report_context}\n--- END REPORT ---\n"
        )

    try:
        completion = generate_groq_completion_with_fallback(
            client=client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": f"Sorry, I encountered an error communicating with the LLM: {str(e)}"}
class ReportRequest(BaseModel):
    prompt: str

@router.post("/report", dependencies=[Depends(verify_token)])
def generate_report(request: ReportRequest):
    from src.config import settings
    from groq import Groq

    if not settings.GROQ_API_KEY:
        return {"response": "Groq API key is not configured. Please add it to your .env file."}

    client = Groq(api_key=settings.GROQ_API_KEY)

    processed_documents = _db_get_all_documents()

    system_prompt = (
        "You are an expert Data Analyst and AI Reporting Assistant for EFL Global. "
        "Your task is to generate a comprehensive, visually appealing report based on the provided system data. "
        "The user will provide a specific request for the report. You must fulfill this request accurately. "
        "CRITICAL INSTRUCTIONS:\n"
        "1. You MUST format your entire response in strict Markdown.\n"
        "2. Use Markdown tables extensively to present data cleanly.\n"
        "3. Use headers (##, ###), bullet points, and bold text to structure the report beautifully.\n"
        "4. Do NOT include any JSON data in your output; present only the analytical, formatted report.\n"
        "5. Be concise yet detailed in your analysis. Summarize key metrics (e.g., total documents, exception counts) if applicable.\n\n"
        "Current System State (Processed Documents):\n"
        f"{json.dumps(processed_documents, indent=2)}"
    )

    try:
        completion = generate_groq_completion_with_fallback(
            client=client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate report: {request.prompt}"}
            ],
            temperature=0.4,
            max_tokens=2048
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": f"Sorry, I encountered an error communicating with the LLM: {str(e)}"}
