from src.agents.state import ProcessState

def validate_gate_pass(state: ProcessState) -> ProcessState:
    """
    Stage 3: Validation Agent
    Cross-references QR Container No with OCR Container No.
    """
    if state.get("error_message") or state.get("validation_status") == "ERROR":
        return state

    qr_payload = state.get("qr_payload")
    ocr_container_no = state.get("ocr_container_no")

    if not qr_payload:
        return {**state, "validation_status": "WARNING"}

    qr_container_no = qr_payload.get("container_no")

    # If OCR hasn't run yet or failed to find container no, we might still proceed 
    # but with a warning, or rely entirely on QR if the confidence is high.
    if not ocr_container_no:
        return {**state, "validation_status": "WARNING"}

    # Validation Logic (as per PDF)
    if qr_container_no == ocr_container_no:
        return {**state, "validation_status": "VALID"}
    else:
        return {**state, "validation_status": "WARNING"}
