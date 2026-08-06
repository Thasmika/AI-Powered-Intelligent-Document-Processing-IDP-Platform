# AI-Powered Intelligent Document Processing (IDP) & QR-Based Automation Agent

## Goal Description
EFL Global processes a massive volume of containers daily, each accompanied by a Gate Pass and supporting documents (Invoices, Packing Lists, Customs Documents, etc.). Currently, these documents are manually processed, leading to incorrect document ordering, misclassification, inconsistent folder naming, and lack of searchable metadata.

This project will build an **AI-Powered Intelligent Document Processing (IDP) Platform** to automate the complete lifecycle of warehouse document processing. This major architectural upgrade introduces a **QR Code-Based Gate Pass Processing layer**. The AI Agent will automatically detect, read, and validate QR codes on Gate Passes, utilizing the QR data as the digital key that connects physical warehouse documents to the enterprise system. This guarantees near-perfect accuracy in container matching, automated folder generation, and real-time website synchronization.

## User Review Required

> [!IMPORTANT]  
> The architecture has been updated to match the **v5.1 Final Architecture Update**. The system now heavily relies on a **QR Code Recognition Agent** for initial processing of Gate Passes, bypassing full-page OCR for core routing and utilizing Azure Document Intelligence for the remaining classification and validation.

## Open Questions

> [!WARNING]  
> 1. **QR Code Format**: Do you have a sample QR code image or Gate Pass PDF we can test the ZXing/ZBar integration with to verify the expected JSON payload?
> 2. **Authentication**: For the backend services and REST API integration in Phase 6, do you have an existing Identity Provider, or should we build a standalone JWT authentication flow?

## Proposed Changes

We will build the system using Python and structure it as a FastAPI + LangGraph application, orchestrated as specialized AI micro-agents operating as a state machine.

### Enterprise Infrastructure & Config
- **Containerization & Orchestration**: Provide `docker-compose.yml` for local dev (PostgreSQL, FastAPI).
- **Storage**: Set up Azure Blob Storage for storing the final sequenced PDFs and `QR_Metadata.json`.
- **Monitoring & Telemetry**: Integrate structured logging (e.g., Azure Application Insights or Prometheus) to track AI agent latency, OCR success rates, and API performance.
- **Dependencies**: Setup `requirements.txt` with `fastapi`, `langgraph`, `opencv-python`, `pyzbar` (or `zxing`), `azure-ai-formrecognizer`, `sqlalchemy`, etc.

### Core Application Structure
- `src/main.py`: FastAPI application entry point.
- `src/config.py`: Environment variable loading.
- `src/database/`: PostgreSQL JSONB schema definition.

### AI Agents & Orchestration (LangGraph)
- **Phase 1: Ingestion, Splitting & QR Processing**
  - `src/agents/intake_agent.py` (Document Intake Agent): Monitors scanner output folders and batches new PDFs.
  - `src/agents/splitter_agent.py` (Document Splitting Agent): Processes large batched PDFs from scanners, detects new Gate Passes (via QR presence or layout), and splits them into logical document sets per container. Passes them to the QR Agent.
  - `src/agents/qr_agent.py` (QR Code Recognition Agent): Detects QR region, decodes data, and validates JSON schema.
    - Tech Stack: OpenCV, ZBar/ZXing
    - Fallback: GPT-4o Vision / Azure AI Vision
- **Phase 2: Validation, External Sync & NLP Classification**
  - `src/agents/validation_agent.py` (Gate Pass Validation Agent): Cross-references the QR payload against standard OCR extraction and existing database records. Also performs **WMS/ERP data validation** (via API or DB query) to ensure the Container ID is expected and active.
  - `src/agents/classification_agent.py` (Document Classification Agent): Uses Azure Document Intelligence to classify all supporting pages (Invoice, Packing List, etc.) and strictly sequences them behind the Gate Pass.
- **Phase 3: Folder Management, Storage & Exception Handling**
  - `src/agents/folder_engine.py`: Creates structured document folders using a highly specific naming convention to prevent collisions on high-volume days: `YYYY-MM-DD_Container-[ContainerNumber]_GP-[GatePassID]/`. Saves `QR_Metadata.json` and linked, sequenced documents (`01_GatePass.pdf`, `02_Invoice.pdf`, etc.) to Azure Blob Storage.
  - **Exception Management (DLQ)**: The LangGraph state machine includes a Dead-Letter Queue / Human-in-the-loop (HITL) routing for documents that fail QR detection, classification, or validation, ensuring no documents are lost silently.
- `src/agents/graph.py`: The LangGraph state machine orchestrating the AI micro-agents.

### Website REST API & Frontend UI Integration
- `src/api/routes.py`: REST APIs in FastAPI to sync data with the EFL Portal, ensuring documents can be queried via perfect metadata.
- **Security & Authentication**: Implement robust authentication (e.g., JWT, OAuth2, or API Keys) to secure sensitive warehouse document data exposed via the REST endpoints.
- **Frontend UI Components**: Develop the EFL portal views to consume the API, specifically:
  - **Container Dashboard (Master View)**: A data grid showing processed Gate Passes and their status.
  - **Folder Explorer View & Search**: An interface that displays the many folders created by the system (organized by date and container). Includes a global **Search Bar** where users can input date or container details to instantly locate the specific folder, open it, and view the correctly sequenced documents (always starting with the Gate Pass, followed by supporting documents).
  - **Document Workspace (Detail View)**: An interface showing extracted metadata alongside an embedded PDF viewer with tabbed navigation for sequenced documents.
  - **Exception Dashboard**: A UI for the Dead-Letter Queue where human operators can manually review and correct documents that failed validation.
  - **AI Assistance Chat Bot**: An integrated AI assistant on the website, hooked into the backend system logic. It allows users to intuitively ask questions about container statuses, system features, and immediately get actionable information based on live IDP data.

## Verification Plan

### Automated Tests
- Create unit tests for `qr_agent.py` to verify it correctly decodes the mock QR payload (`gate_pass_no`, `container_no`, etc.).
- Validate the state machine transitions in `graph.py` to ensure it falls back to GPT-4o Vision if local QR reading fails.

### Manual Verification
- Deploy to a Warehouse Sandbox for User Acceptance Testing (UAT).
- Run full container document batches through the ingestion folder and verify the correct folders, JSON, and sequenced PDFs are generated in Azure Blob Storage.
