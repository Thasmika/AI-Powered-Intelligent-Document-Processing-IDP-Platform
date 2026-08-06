from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from src.agents.graph import app as workflow_app
from src.agents.intake_agent import get_new_scanned_files, simulate_intake_process
import time
import asyncio
import json

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

# Mock database
processed_documents = []

def process_background_file(file_path):
    state = simulate_intake_process(file_path)
    result_state = workflow_app.invoke(state)
    
    # Store result in mock DB
    doc_id = f"doc_{int(time.time()*1000)}"
    doc_data = {
        "id": doc_id,
        "container_no": result_state.get("qr_payload", {}).get("container_no", "Unknown") if result_state.get("qr_payload") else "Unknown",
        "gate_pass_no": result_state.get("qr_payload", {}).get("gate_pass_no", "Unknown") if result_state.get("qr_payload") else "Unknown",
        "status": result_state.get("validation_status", "UNKNOWN"),
        "folder_path": result_state.get("final_folder_path"),
        "error_message": result_state.get("error_message")
    }
    processed_documents.append(doc_data)
    
    # Broadcast update to frontend via WebSocket
    message = json.dumps({"type": "DOCUMENT_PROCESSED", "data": doc_data})
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(manager.broadcast(message))
        else:
            loop.run_until_complete(manager.broadcast(message))
    except Exception as e:
        print(f"WebSocket broadcast error: {e}")

from src.agents.splitter_agent import split_pdf_batch
from src.config import settings
import os

@router.post("/trigger-ingestion", dependencies=[Depends(verify_token)])
def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Triggers the LangGraph workflow for all new scanned PDFs.
    """
    files = list(get_new_scanned_files())
    
    # Run the Splitter Agent first to split large batches into logical documents
    output_dir = settings.SCANNER_INPUT_DIR / "split_docs"
    
    total_split_files = []
    for f in files:
        split_files = split_pdf_batch(str(f), str(output_dir))
        total_split_files.extend(split_files)
        
        # Optional: Delete or move original batch file after splitting
        # os.remove(f)

    # Process each logically split document
    for split_f in total_split_files:
        background_tasks.add_task(process_background_file, split_f)
        
    return {"message": f"Started processing {len(total_split_files)} split documents from {len(files)} batch files"}

@router.get("/documents", response_model=List[DocumentResponse], dependencies=[Depends(verify_token)])
def get_documents():
    """
    Returns all processed documents for the Master Data Grid.
    """
    return processed_documents

@router.get("/documents/exceptions", response_model=List[DocumentResponse], dependencies=[Depends(verify_token)])
def get_exceptions():
    """
    Returns documents that routed to Dead-Letter Queue (DLQ).
    """
    return [doc for doc in processed_documents if doc["status"] in ["WARNING", "ERROR"]]
