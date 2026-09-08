import re
import os
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
        pdf_files = state.get("pdf_files", [])
        if not pdf_files:
            return {**state, "error_message": "No PDF files found in folder."}
            
        qr_payload = None
        pdf_text = ""
        
        for file_path in pdf_files:
            # Load image using OpenCV (if image) or PyMuPDF (if PDF)
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                pdf_text = "".join([page.get_text() for page in doc])
                page = doc[0] # Assume QR is on the first page of the specific document
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
                continue

            # Decode QR codes
            decoded_objects = decode(image)
            
            for obj in decoded_objects:
                if obj.type != 'QRCODE':
                    continue
                data_str = obj.data.decode('utf-8')
                try:
                    # Attempt JSON parsing
                    parsed_json = json.loads(data_str)
                    
                    lower_json = {k.lower().replace(" ", "_"): v for k, v in parsed_json.items()}
                    gp_no = (
                        lower_json.get('id') or 
                        lower_json.get('id_no') or
                        lower_json.get('gate_pass_id') or
                        lower_json.get('gatepass_id') or
                        lower_json.get('doc_no') or 
                        lower_json.get('document_no') or
                        lower_json.get('gate_pass_no') or 
                        lower_json.get('gatepass_no') or
                        lower_json.get('gatepass')
                    )
                    
                    if gp_no:
                        parsed_json['gate_pass_no'] = str(gp_no)
                    if 'container_no' not in lower_json:
                        parsed_json['container_no'] = "UNKNOWN"
                        
                    valid_payload = GatePassQRPayload(**parsed_json)
                    qr_payload = parsed_json  # Preserve all original fields
                    qr_payload['gate_pass_no'] = valid_payload.gate_pass_no
                    qr_payload['container_no'] = valid_payload.container_no
                    break
                except (json.JSONDecodeError, ValidationError, TypeError):
                    # Attempt key-value pair parsing
                    data_dict = {}
                    for item in data_str.replace('\n', ';').split(';'):
                        if ':' in item:
                            k, v = item.split(':', 1)
                            data_dict[k.strip().lower().replace(" ", "_")] = v.strip()
                    
                    gp_no = (
                        data_dict.get('id') or 
                        data_dict.get('id_no') or
                        data_dict.get('gate_pass_id') or
                        data_dict.get('gatepass_id') or
                        data_dict.get('doc_no') or 
                        data_dict.get('document_no') or
                        data_dict.get('gate_pass_no') or 
                        data_dict.get('gatepass_no') or
                        data_dict.get('gatepass')
                    )
                    
                    if gp_no:
                        qr_payload = data_dict.copy()
                        qr_payload["gate_pass_no"] = gp_no
                        qr_payload["container_no"] = data_dict.get('container_no', 'UNKNOWN')
                        break
                    
                    # Legacy split logic (fallback if dictionary extraction yielded no valid ID)
                    parts = data_str.replace('\n', ';').split(';')
                    if len(parts) >= 1:
                        qr_payload = {
                            "gate_pass_no": parts[0].strip(),
                            "container_no": parts[3].strip() if len(parts) > 3 else "UNKNOWN"
                        }
                        break
                    continue

            if qr_payload:
                break 

        # --- OCR Text Fallback & Augmentation (Regex-based) ---
        ocr_payload = _extract_payload_from_text(pdf_files, state.get("source_pdf"))

        if qr_payload:
            # If QR code was found, augment it with any extra fields found via OCR
            if ocr_payload:
                for k, v in ocr_payload.items():
                    # Only add if it doesn't exist, or if the current value is missing/unknown
                    if k not in qr_payload or qr_payload[k] in [None, "", "UNKNOWN", "Unknown"]:
                        qr_payload[k] = v
        else:
            qr_payload = ocr_payload

        if not qr_payload:
            return {**state, "validation_status": "WARNING", "error_message": "No valid QR Code or identifiable text found in documents"}

        return {**state, "qr_payload": qr_payload, "validation_status": "PENDING"}
        
    except Exception as e:
        return {**state, "validation_status": "ERROR", "error_message": str(e)}


def _extract_payload_from_text(pdf_files: list, source_pdf: str = None) -> dict | None:
    """
    OCR text fallback: reads all PDF text and uses regex to extract
    gate_pass_no and container_no from document content.
    Prioritises files with 'gatepass' in the filename.
    """
    combined_text = ""

    # Prioritize files named 'GatePass' or similar
    ordered_files = sorted(
        pdf_files,
        key=lambda f: 0 if "gatepass" in os.path.basename(f).lower().replace("_", "").replace("-", "").replace(" ", "") else 1
    )

    for file_path in ordered_files:
        if not file_path.lower().endswith('.pdf'):
            continue
        try:
            doc = fitz.open(file_path)
            for page in doc:
                page_text = page.get_text("text", sort=True)
                # Fix known font mapping issues where 'D' is extracted as a checkbox (\u25a1)
                page_text = page_text.replace('\u25a1', 'D')
                combined_text += page_text + "\n"
            doc.close()
        except Exception:
            continue

    if combined_text.strip():
        safe_preview = combined_text[:500].encode("ascii", errors="replace").decode("ascii")
        print(f"[QR Agent - OCR Fallback] Scanning text (first 500 chars):\n{safe_preview}")

    gate_pass_no = None
    container_no = None
    destination_location = None

    def _extract_field(label, text):
        # Try finding value before label (common in PDF block ordering)
        m = re.search(rf"([^\n]+)\n\s*{label}\s*[:\-]", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not re.search(r"^[A-Z\s]+:$", val) and val:
                return val
                
        # Try finding value after label on same line (stop at next column header)
        m = re.search(rf"{label}\s*[:\-][ \t]*([^\n]+)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # If it captures another field header like 'VEHICLE OUT TIME:', reject it
            if not re.search(r"^[A-Z\s]+:$", val) and val:
                return val
                
        # Try finding value on next line
        m = re.search(rf"{label}\s*[:\-]\s*\n([^\n]+)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not re.search(r"^[A-Z\s]+:$", val) and val:
                return val
                
        return None

    # Gate Pass Number patterns (most specific → least specific)
    gp_patterns = [
        r"\b(\d{5,8})\b\s*GATE\s*PASS",
        r"(?<!APPOINTMENT\s)(?:id|doc(?:ument)?\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9_-]{4,15})",
        r"(?:gate\s*pass\s*(?:no\.?|number|#)?\s*[:\-]?\s*)(?!08\b|DESTINATION|VEHICLE)(\S+)",
        r"GP[-\s]?([\d]{4,10})",
        r"(?:Pass\s*No\.?[:\s]*)(\S+)",
    ]
    for pattern in gp_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            gate_pass_no = match.group(1).strip().rstrip('.,;')
            break

    # Container Number patterns
    cont_patterns = [
        r"(?:container\s*(?:no\.?|number|id|#)?\s*[:\-]?\s*)([A-Z]{3,4}[U|J|Z]\d{7})",  # ISO format
        r"\b([A-Z]{3,4}[UJZ]\d{6}\d)\b",                                                  # ISO loose
        r"(?:container\s*(?:no\.?|number|id|#)?\s*[:\-]?\s*)(?!TYPE\b)([\w\-]{4,15})",
        r"(?:Cont\.?\s*No\.?[:\s]*)(\S+)",
    ]
    for pattern in cont_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            container_no = match.group(1).strip().rstrip('.,;')
            break

    destination_location = _extract_field(r"DESTINATION\s*LOCATION", combined_text) or _extract_field(r"DESTINATION", combined_text)
    
    grn_no = _extract_field(r"GRN\s*NO\.?", combined_text)
    date_time = _extract_field(r"DATE", combined_text) or _extract_field(r"FINISHED TIME", combined_text)
    customer = _extract_field(r"CUSTOMER", combined_text)
    received_from = _extract_field(r"RECEIVED FROM", combined_text)
    supplier = _extract_field(r"SUPPLIER", combined_text)
    container_type = _extract_field(r"CONTAINER TYPE", combined_text)

    # Last resort: derive gate_pass_no from the filename itself
    if not gate_pass_no:
        files_to_check = [source_pdf] if source_pdf else ordered_files
        for fp in files_to_check:
            if not fp: continue
            stem = os.path.splitext(os.path.basename(fp))[0]
            stem = re.sub(r"(?i)^(unsplit_|batch_split_\d+_)", "", stem)
            cleaned = re.sub(r"(?i)(gatepass|gate_pass|gate pass|gp[-_]?)", "", stem).strip("_- ")
            if cleaned:
                gate_pass_no = cleaned
                break

    if gate_pass_no:
        # Sanitize: strip non-ASCII chars (e.g. ☐ checkbox symbols from PDF form fields)
        # and collapse any leading/trailing whitespace to produce a clean folder name.
        gate_pass_no = re.sub(r"[^\x20-\x7E]", "", gate_pass_no).strip()
        if container_no:
            container_no = re.sub(r"[^\x20-\x7E]", "", container_no).strip()

        if gate_pass_no:
            payload = {
                "gate_pass_no": gate_pass_no,
                "container_no": container_no or "UNKNOWN",
                "destination_location": destination_location or "Unknown",
                "grn_no": grn_no,
                "date_time": date_time,
                "customer": customer,
                "received_from": received_from,
                "supplier": supplier,
                "container_type": container_type
            }
            return {k: v for k, v in payload.items() if v is not None}

    return None
