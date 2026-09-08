import os
import sys
import json
import qrcode
from pathlib import Path

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.intake_agent import simulate_intake_process
from src.agents.graph import app as workflow_app

def generate_mock_qr_image(payload, filename):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"Generated mock QR image: {filename}")
    return filename

def test_valid_pipeline():
    print("--- Testing Valid Pipeline ---")
    payload = {"Customer": "LA", "GatePass": "VEHICLE", "id_no": "122844"}
    img_path = generate_mock_qr_image(payload, "test_valid_qr.png")
    
    state = simulate_intake_process(Path(img_path))
    result = workflow_app.invoke(state)
    
    print("\nResult State:")
    print(json.dumps(result, indent=2))
    print("-" * 30)

def test_invalid_container():
    print("--- Testing Invalid Container (DLQ Routing) ---")
    payload = {"gate_pass_no": "700068", "container_no": "UNKNOWN-CONT"}
    img_path = generate_mock_qr_image(payload, "test_invalid_qr.png")
    
    state = simulate_intake_process(Path(img_path))
    result = workflow_app.invoke(state)
    
    print("\nResult State:")
    print(json.dumps(result, indent=2))
    print("-" * 30)

if __name__ == "__main__":
    # Ensure scanner input dir exists
    from src.config import settings
    settings.SCANNER_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    test_valid_pipeline()
    test_invalid_container()
