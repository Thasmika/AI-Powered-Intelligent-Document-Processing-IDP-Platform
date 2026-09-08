from src.agents.state import ProcessState

def validate_gate_pass(state: ProcessState) -> ProcessState:
    """
    Stage 3: Validation Agent
    Validates that the QR/OCR payload has a non-empty gate_pass_no.
    Optionally cross-references QR Container No with OCR Container No if available.

    NOTE: The WMS/ERP whitelist has been removed so that real scanned gate passes
    are not blocked. Add live WMS lookup logic here when the API is available.
    """
    if state.get("error_message") or state.get("validation_status") == "ERROR":
        return state

    qr_payload = state.get("qr_payload")
    ocr_container_no = state.get("ocr_container_no")

    if not qr_payload:
        return {**state, "validation_status": "WARNING", "error_message": "No QR/OCR payload found"}

    gate_pass_no = qr_payload.get("gate_pass_no", "").strip()
    qr_container_no = qr_payload.get("container_no", "").strip()

    # Basic sanity check: gate pass number must be present
    if not gate_pass_no or gate_pass_no in ("UNKNOWN", "UNKNOWN-GP", ""):
        return {**state, "validation_status": "WARNING", "error_message": "Gate Pass number is missing or unreadable"}

    # If both QR and OCR container numbers are available, cross-check them
    if ocr_container_no and qr_container_no and qr_container_no != "UNKNOWN":
        if qr_container_no != ocr_container_no:
            return {**state, "validation_status": "WARNING",
                    "error_message": f"QR container ({qr_container_no}) and OCR container ({ocr_container_no}) mismatch"}

    # All checks passed
    return {**state, "validation_status": "VALID"}
