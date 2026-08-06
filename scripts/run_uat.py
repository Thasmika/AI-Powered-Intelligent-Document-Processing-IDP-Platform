import os
import sys
import json
import fitz  # PyMuPDF
import qrcode
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import settings
from src.agents.splitter_agent import split_pdf_batch
from src.agents.intake_agent import simulate_intake_process
from src.agents.graph import app as workflow_app

def generate_qr_image(payload, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    return filename

def create_mock_batch_pdf():
    print("Generating mock batch PDF...")
    doc = fitz.open()
    
    # ---------------------------------------------------------
    # Document 1: Gate Pass for CONT-A1
    # ---------------------------------------------------------
    page1 = doc.new_page()
    page1.insert_text((50, 50), "EFL GLOBAL WAREHOUSE", fontsize=20)
    page1.insert_text((50, 80), "GATE PASS:", fontsize=16)
    page1.insert_text((50, 100), "IN GATE SECURITY", fontsize=16)
    page1.insert_text((50, 150), "Container: CONT-A1\nGate Pass ID: GP-1001", fontsize=12)
    
    qr_img1 = generate_qr_image({"gate_pass_no": "GP-1001", "container_no": "CONT-A1"}, "tmp_qr1.png")
    page1.insert_image(fitz.Rect(50, 200, 250, 400), filename=qr_img1)
    
    # Document 1: Supporting Document (Invoice)
    page2 = doc.new_page()
    page2.insert_text((50, 50), "COMMERCIAL INVOICE", fontsize=20)
    page2.insert_text((50, 100), "Container: CONT-A1\nTotal: $5000", fontsize=12)

    # ---------------------------------------------------------
    # Document 2: Gate Pass for CONT-B2 (Will trigger DLQ because it's not in our mock WMS list)
    # ---------------------------------------------------------
    page3 = doc.new_page()
    page3.insert_text((50, 50), "EFL GLOBAL WAREHOUSE", fontsize=20)
    page3.insert_text((50, 80), "GATE PASS:", fontsize=16)
    page3.insert_text((50, 100), "IN GATE SECURITY", fontsize=16)
    page3.insert_text((50, 150), "Container: CONT-B2\nGate Pass ID: GP-1002", fontsize=12)
    
    qr_img2 = generate_qr_image({"gate_pass_no": "GP-1002", "container_no": "CONT-B2"}, "tmp_qr2.png")
    page3.insert_image(fitz.Rect(50, 200, 250, 400), filename=qr_img2)

    batch_path = settings.SCANNER_INPUT_DIR / "scanner_batch_001.pdf"
    doc.save(batch_path)
    doc.close()
    
    # Cleanup temp images
    os.remove("tmp_qr1.png")
    os.remove("tmp_qr2.png")
    
    print(f"Batch PDF saved to: {batch_path}")
    return batch_path

def run_uat_pipeline():
    print("\n--- Starting User Acceptance Testing (UAT) Pipeline ---")
    batch_pdf_path = create_mock_batch_pdf()
    
    print("\n[Phase 1] Running Splitter Agent...")
    output_dir = settings.SCANNER_INPUT_DIR / "split_docs"
    split_files = split_pdf_batch(str(batch_pdf_path), str(output_dir))
    
    print(f"Split batch into {len(split_files)} logical documents:")
    for f in split_files:
        print(f"  -> {f}")
        
    print("\n[Phase 2-5] Running LangGraph Orchestration on Split Documents...")
    for idx, file_path in enumerate(split_files):
        print(f"\nProcessing Document {idx + 1}: {file_path}")
        state = simulate_intake_process(Path(file_path))
        
        # We need to hack our mock WMS database in validation_agent for CONT-A1 to pass
        import src.agents.validation_agent as va
        if "CONT-A1" not in va.validate_gate_pass.__code__.co_consts:
            # We'll just patch the expected containers dynamically for testing
            pass
            
        result = workflow_app.invoke(state)
        
        status = result.get("validation_status")
        print(f"  -> Validation Status: {status}")
        if status == "WARNING" or status == "ERROR":
            print(f"  -> Routed to DLQ. Error: {result.get('error_message')}")
        else:
            print(f"  -> Successfully stored in: {result.get('final_folder_path')}")
            
    print("\n--- UAT Pipeline Complete ---")

if __name__ == "__main__":
    run_uat_pipeline()
