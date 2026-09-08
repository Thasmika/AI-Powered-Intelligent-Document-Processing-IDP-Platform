from langgraph.graph import StateGraph, END
from src.agents.state import ProcessState
from src.agents.splitter_agent import split_scanner_pdf
from src.agents.qr_agent import process_qr_code
from src.agents.validation_agent import validate_gate_pass
from src.agents.classification_agent import classify_document
from src.agents.folder_engine import folder_management
from src.telemetry import track_performance


@track_performance("ocr_extraction")
def ocr_extraction(state: ProcessState) -> ProcessState:
    # Placeholder for standard OCR
    if state.get("error_message"):
        return state
    # Simulated OCR result — uses QR payload if available
    return {**state, "ocr_container_no": state.get("qr_payload", {}).get("container_no") if state.get("qr_payload") else None}


@track_performance("dlq_routing")
def dlq_routing(state: ProcessState) -> ProcessState:
    # Dead-Letter Queue processing
    print(f"[DLQ] Document routed to DLQ: {state.get('source_pdf') or state.get('folder_path')}. "
          f"Reason: {state.get('error_message')}")
    return state


def route_after_validation(state: ProcessState) -> str:
    status = state.get("validation_status")
    if status == "VALID":
        return "classification"
    else:
        return "dlq"


# ---------------------------------------------------------------------------
# Build the LangGraph workflow
# ---------------------------------------------------------------------------

workflow = StateGraph(ProcessState)

# Stage 1b — Split the big scanner PDF into individual sub-documents
workflow.add_node("splitting",       track_performance("splitter_agent")(split_scanner_pdf))

# Stage 2 — QR / OCR extraction from the Gate Pass sub-PDF
workflow.add_node("qr_processing",   track_performance("qr_agent")(process_qr_code))

# (optional) full-page OCR pass
workflow.add_node("ocr_processing",  ocr_extraction)

# Stage 3 — Validate gate pass identity
workflow.add_node("validation",      track_performance("validation_agent")(validate_gate_pass))

# Stage 3b — Classify each sub-document
workflow.add_node("classification",  track_performance("classification_agent")(classify_document))

# Stage 4 — Create the named folder and copy files
workflow.add_node("storage",         track_performance("folder_engine")(folder_management))

# Dead-Letter Queue
workflow.add_node("dlq",             dlq_routing)

# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

# Entry point is now the splitter (no more manual folder scanning of PDFs)
workflow.set_entry_point("splitting")

workflow.add_edge("splitting",     "qr_processing")
workflow.add_edge("qr_processing", "ocr_processing")
workflow.add_edge("ocr_processing","validation")

# Conditional routing after validation
workflow.add_conditional_edges("validation", route_after_validation, {
    "classification": "classification",
    "dlq":            "dlq",
})

workflow.add_edge("classification", "storage")
workflow.add_edge("storage",        END)
workflow.add_edge("dlq",            END)

# Compile
app = workflow.compile()
