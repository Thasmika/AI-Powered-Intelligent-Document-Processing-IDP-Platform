import os
import shutil
import fitz  # PyMuPDF
from typing import List
from src.agents.state import ProcessState


# ---------------------------------------------------------------------------
# Page-level boundary detection
# ---------------------------------------------------------------------------

def detect_gate_pass_boundary(page) -> bool:
    """
    Returns True if this PDF page is the START of a Gate Pass document.
    Checks for structural keywords: 'GATE PASS:' AND 'IN GATE SECURITY'.
    """
    text = page.get_text("text").upper()
    return "GATE PASS:" in text and "IN GATE SECURITY" in text


# ---------------------------------------------------------------------------
# Core splitter: big PDF → individual sub-PDFs
# ---------------------------------------------------------------------------

def split_pdf_batch(batch_pdf_path: str, output_dir: str) -> List[str]:
    """
    Reads a single large scanner PDF and splits it into logical document
    groups (sub-PDFs).  Each group begins at a Gate Pass page.

    Each sub-PDF is written to `output_dir` as:
        batch_split_0.pdf   ← Gate Pass + its trailing pages
        batch_split_1.pdf   ← next Gate Pass + its trailing pages
        …

    If no Gate Pass boundary is ever found the whole PDF is copied as
    'unsplit_{filename}.pdf' so downstream agents can route it to the DLQ.

    Returns a list of absolute paths to the newly created sub-PDFs.
    """
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(batch_pdf_path)
    split_paths: List[str] = []

    current_writer = None
    current_doc_index = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        if detect_gate_pass_boundary(page):
            # Save the previous group (if any) before starting a new one
            if current_writer is not None:
                out_path = os.path.join(output_dir, f"batch_split_{current_doc_index}.pdf")
                current_writer.save(out_path)
                current_writer.close()
                split_paths.append(out_path)
                current_doc_index += 1

            current_writer = fitz.open()

        # Always append the current page to the open writer (if we've seen a boundary)
        if current_writer is not None:
            current_writer.insert_pdf(doc, from_page=page_num, to_page=page_num)

    # Flush the last group
    if current_writer is not None:
        out_path = os.path.join(output_dir, f"batch_split_{current_doc_index}.pdf")
        current_writer.save(out_path)
        current_writer.close()
        split_paths.append(out_path)
    else:
        # No Gate Pass boundary found → copy whole PDF as unsplit for DLQ routing
        unsplit_name = f"unsplit_{os.path.basename(batch_pdf_path)}"
        out_path = os.path.join(output_dir, unsplit_name)
        shutil.copy2(batch_pdf_path, out_path)
        split_paths.append(out_path)

    doc.close()
    return split_paths


# ---------------------------------------------------------------------------
# LangGraph node: wraps split_pdf_batch and updates workflow state
# ---------------------------------------------------------------------------

def split_scanner_pdf(state: ProcessState) -> ProcessState:
    """
    Stage 1b: Splitter Agent (LangGraph node)

    Reads the original big scanner PDF stored in state['source_pdf'],
    splits it into sub-PDFs inside a temp directory, and updates state so
    downstream agents (QR, Classification) receive individual document paths.

    The temp directory is stored in state['split_docs_dir'] so the Folder
    Engine can clean it up once documents are copied to efl_documents/.
    """
    if state.get("error_message"):
        return state

    source_pdf = state.get("source_pdf")
    if not source_pdf or not os.path.exists(source_pdf):
        return {**state, "error_message": "Source PDF missing or not found for splitting."}

    # Build temp directory path: scanner_input/split_docs/{pdf_stem}/
    from src.config import settings
    pdf_stem = os.path.splitext(os.path.basename(source_pdf))[0]
    # Sanitise the stem so it's safe as a directory name
    safe_stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in pdf_stem).strip()
    split_dir = str(settings.SCANNER_INPUT_DIR / "split_docs" / safe_stem)

    print(f"[Splitter] Splitting '{os.path.basename(source_pdf)}' -> {split_dir}")

    try:
        split_paths = split_pdf_batch(source_pdf, split_dir)
    except Exception as e:
        return {**state, "error_message": f"PDF splitting failed: {e}"}

    if not split_paths:
        return {**state, "error_message": "No sub-PDFs produced from scanner PDF."}

    print(f"[Splitter] Produced {len(split_paths)} sub-document(s):")
    for p in split_paths:
        print(f"  - {os.path.basename(p)}")

    return {
        **state,
        "pdf_files": split_paths,
        "folder_path": split_dir,
        "split_docs_dir": split_dir,
    }
