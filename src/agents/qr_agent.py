import fitz  # PyMuPDF
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import json
from pydantic import BaseModel, ValidationError
from src.agents.state import ProcessState

class GatePassQRPayload(BaseModel):
    gate_pass_no: str
    container_no: str

def process_qr_code(state: ProcessState) -> ProcessState:
    """
    Stage 2 (Stream A): QR Code Recognition Agent
    Detects and decodes the QR code from the document image or PDF.
    Validates the JSON payload.
    """
    try:
        file_path = state["file_path"]
        
        # Load image using OpenCV (if image) or PyMuPDF (if PDF)
        if file_path.lower().endswith('.pdf'):
            doc = fitz.open(file_path)
            page = doc[0] # Gate pass is always the first page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Render at 2x resolution
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                image = cv2.cvtColor(img_data, cv2.COLOR_BGRA2BGR)
            else:
                image = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            doc.close()
        else:
            image = cv2.imread(file_path)
            
        if image is None:
            return {**state, "error_message": "Could not read image or PDF file."}

        # Decode QR codes
        decoded_objects = decode(image)
        
        qr_payload = None
        for obj in decoded_objects:
            try:
                # Assume the QR code contains JSON string as per architecture
                parsed_json = json.loads(obj.data.decode('utf-8'))
                
                # Validate JSON schema using Pydantic
                valid_payload = GatePassQRPayload(**parsed_json)
                qr_payload = valid_payload.model_dump()
                break # Use the first valid JSON QR code
            except (json.JSONDecodeError, ValidationError):
                continue

        if not qr_payload:
            # Fallback logic would go here (e.g., Azure AI Vision or GPT-4o)
            # For now, we simulate the warning state if QR is not found
            return {**state, "validation_status": "WARNING", "error_message": "No valid JSON QR Code found"}

        return {**state, "qr_payload": qr_payload, "validation_status": "PENDING"}
        
    except Exception as e:
        return {**state, "validation_status": "ERROR", "error_message": str(e)}
