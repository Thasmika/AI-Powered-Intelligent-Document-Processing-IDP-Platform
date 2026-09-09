import os
import sys
import json
import qrcode
import requests
from pathlib import Path

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import settings

def generate_mock_qr_image(payload, filename):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"Generated mock QR image: {filename}")
    return filename

def test_folder_pipeline():
    print("--- Testing Folder Pipeline ---")
    
    # 1. Create a fake scanner folder
    from datetime import datetime
    import random
    
    # Simulate real scanner folder format (e.g. 2026-08-17_15-21-10)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    job_folder = Path(settings.SCANNER_INPUT_DIR) / timestamp
    job_folder.mkdir(parents=True, exist_ok=True)
    
    # 2. Generate a valid QR pass as a .png (or pdf, but qr_agent handles png too)
    # Wait, the prompt says scanner outputs PDFs. The qr_agent handles both PDF and images.
    # Intake agent's route.py gets pdfs: `pdf_files = [str(f) for f in folder.glob("*.pdf")]`
    import fitz
    
    payload = {"gate_pass_no": "700067", "container_no": "CONT123"}
    img_path = generate_mock_qr_image(payload, "temp_qr.png")
    
    # Convert image to PDF
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_image(page.rect, filename="temp_qr.png")
    page.insert_text((50, 50), "GATE PASS")
    pdf_doc.save(job_folder / "gatepass.pdf")
    pdf_doc.close()
    
    # Add a dummy invoice PDF
    pdf_doc2 = fitz.open()
    page2 = pdf_doc2.new_page()
    page2.insert_text((50, 50), "This is a fake INVOICE")
    pdf_doc2.save(job_folder / "invoice.pdf")
    pdf_doc2.close()
    
    print(f"Created fake scanner folder with PDFs at: {job_folder}")
    
    # 3. Trigger ingestion API
    # response = requests.post("http://localhost:8000/api/v1/trigger-ingestion?token=dummy-jwt-token")
    # print("API Response:", response.status_code, response.json())
    
    print("-" * 30)

if __name__ == "__main__":
    test_folder_pipeline()
