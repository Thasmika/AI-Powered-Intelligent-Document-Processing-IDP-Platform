import cv2
from pyzbar.pyzbar import decode
import json
from src.agents.state import ProcessState

def process_qr_code(state: ProcessState) -> ProcessState:
    """
    Stage 2 (Stream A): QR Code Recognition Agent
    Detects and decodes the QR code from the document image.
    """
    try:
        # Load image using OpenCV
        image = cv2.imread(state["file_path"])
        if image is None:
            return {**state, "error_message": "Could not read image file."}

        # Decode QR codes
        decoded_objects = decode(image)
        
        qr_payload = None
        for obj in decoded_objects:
            try:
                # Assume the QR code contains JSON string as per architecture
                qr_payload = json.loads(obj.data.decode('utf-8'))
                break # Use the first valid JSON QR code
            except json.JSONDecodeError:
                continue

        if not qr_payload:
            # Fallback logic would go here (e.g., Azure AI Vision or GPT-4o)
            # For now, we simulate the warning state if QR is not found
            return {**state, "validation_status": "WARNING", "error_message": "No valid JSON QR Code found"}

        return {**state, "qr_payload": qr_payload, "validation_status": "PENDING"}
        
    except Exception as e:
        return {**state, "validation_status": "ERROR", "error_message": str(e)}
