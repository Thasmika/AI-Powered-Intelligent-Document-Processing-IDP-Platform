from langgraph.graph import StateGraph, END
from src.agents.state import ProcessState
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
    # Simulated OCR result
    return {**state, "ocr_container_no": state.get("qr_payload", {}).get("container_no") if state.get("qr_payload") else None}

@track_performance("dlq_routing")
def dlq_routing(state: ProcessState) -> ProcessState:
    # Dead-Letter Queue processing
    print(f"Document routed to DLQ: {state.get('file_path')}. Reason: {state.get('error_message')}")
    return state

def route_after_validation(state: ProcessState) -> str:
    status = state.get("validation_status")
    if status == "VALID":
        return "classification"
    else:
        return "dlq"

# Define the graph
workflow = StateGraph(ProcessState)

# Add nodes with Telemetry wrapping
workflow.add_node("qr_processing", track_performance("qr_agent")(process_qr_code))
workflow.add_node("ocr_processing", ocr_extraction)
workflow.add_node("validation", track_performance("validation_agent")(validate_gate_pass))
workflow.add_node("classification", track_performance("classification_agent")(classify_document))
workflow.add_node("storage", track_performance("folder_engine")(folder_management))
workflow.add_node("dlq", dlq_routing)

# Add edges
workflow.set_entry_point("qr_processing")

workflow.add_edge("qr_processing", "ocr_processing")
workflow.add_edge("ocr_processing", "validation")

# Conditional routing after validation
workflow.add_conditional_edges("validation", route_after_validation, {
    "classification": "classification",
    "dlq": "dlq"
})

workflow.add_edge("classification", "storage")
workflow.add_edge("storage", END)
workflow.add_edge("dlq", END)

# Compile graph
app = workflow.compile()

