import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.agents.intake_agent import simulate_intake_process
from src.agents.graph import app as workflow_app
from src.config import settings

def run_load_test(num_documents=10):
    print(f"--- Starting Load Test ({num_documents} documents) ---")
    
    # We will use the already generated test_valid_qr.png from earlier tests to simulate high volume
    # To avoid generating 50 PDFs, we just pass the same image repeatedly.
    test_image = Path("test_valid_qr.png")
    
    if not test_image.exists():
        print("Error: test_valid_qr.png not found. Run test_pipeline.py first.")
        return
        
    start_time = time.time()
    
    success_count = 0
    error_count = 0
    
    for i in range(num_documents):
        state = simulate_intake_process(test_image)
        result = workflow_app.invoke(state)
        
        if result.get("validation_status") == "WARNING" or result.get("validation_status") == "ERROR":
            error_count += 1
        else:
            success_count += 1
            
        if (i + 1) % 5 == 0:
            print(f"Processed {i + 1}/{num_documents}...")
            
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n--- Load Test Results ---")
    print(f"Total Documents Processed: {num_documents}")
    print(f"Successful: {success_count}")
    print(f"Failed/DLQ: {error_count}")
    print(f"Total Time: {duration:.2f} seconds")
    print(f"Average Time per Document: {(duration / num_documents):.2f} seconds")
    print(f"Throughput: {(num_documents / duration):.2f} docs/sec")
    print("-------------------------")

if __name__ == "__main__":
    # Ensure test_valid_qr.png exists
    import test_pipeline
    test_pipeline.generate_mock_qr_image({"gate_pass_no": "GP-LOAD", "container_no": "CONT123"}, "test_valid_qr.png")
    
    run_load_test(20)
