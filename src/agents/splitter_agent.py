import os
import fitz  # PyMuPDF
from typing import List
import cv2
import numpy as np

def detect_gate_pass_boundary(page) -> bool:
    """
    Analyzes a PDF page to determine if it is the start of a new Gate Pass.
    Checks for structural keywords like 'GATE PASS:' or 'IN GATE SECURITY'.
    """
    text = page.get_text("text").upper()
    
    # Based on the sample provided:
    # "GATE PASS:" and "IN GATE SECURITY" are strong indicators
    if "GATE PASS:" in text and "IN GATE SECURITY" in text:
        return True
        
    return False

def split_pdf_batch(batch_pdf_path: str, output_dir: str) -> List[str]:
    """
    Takes a massive batch PDF from the scanner and splits it into logical 
    document groups (sub-PDFs), where each group begins with a Gate Pass.
    Returns a list of paths to the newly split PDFs.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    doc = fitz.open(batch_pdf_path)
    split_paths = []
    
    current_writer = None
    current_doc_index = 0
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # If this page is a Gate Pass, we start a new sub-document
        if detect_gate_pass_boundary(page):
            if current_writer is not None:
                # Save the previous document group
                out_path = os.path.join(output_dir, f"batch_split_{current_doc_index}.pdf")
                current_writer.save(out_path)
                current_writer.close()
                split_paths.append(out_path)
                current_doc_index += 1
            
            # Start a new document group
            current_writer = fitz.open()
            
        if current_writer is not None:
            current_writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
    # Save the last document group
    if current_writer is not None:
        out_path = os.path.join(output_dir, f"batch_split_{current_doc_index}.pdf")
        current_writer.save(out_path)
        current_writer.close()
        split_paths.append(out_path)
        
    doc.close()
    return split_paths
