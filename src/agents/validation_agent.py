from src.agents.state import ProcessState

def validate_gate_pass(state: ProcessState) -> ProcessState:
    """
    Stage 3: Validation Agent
    Cross-references QR Container No with OCR Container No.
    Also performs WMS/ERP data validation to ensure Container ID is expected.
    """
    if state.get("error_message") or state.get("validation_status") == "ERROR":
        return state

    qr_payload = state.get("qr_payload")
    ocr_container_no = state.get("ocr_container_no")

    if not qr_payload:
        return {**state, "validation_status": "WARNING"}

    qr_container_no = qr_payload.get("container_no")
    
    # Mock WMS/ERP database of expected active containers
    expected_containers = ["CONT123", "CONT456", "CONT789", "CONT-A1"]

    if qr_container_no not in expected_containers:
        # If not expected, we can mark it as WARNING or DLQ
        return {**state, "validation_status": "WARNING", "error_message": "Container ID not found in WMS/ERP"}

    # Validation Logic (as per PDF)
    # If OCR hasn't run yet or failed to find container no, we rely entirely on QR.
    if not ocr_container_no:
        # We might still proceed with VALID if it matches WMS
        return {**state, "validation_status": "VALID"}

    if qr_container_no == ocr_container_no:
        return {**state, "validation_status": "VALID"}
    else:
        return {**state, "validation_status": "WARNING", "error_message": "QR and OCR Container No mismatch"}

