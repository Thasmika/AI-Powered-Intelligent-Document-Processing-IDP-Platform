# Technical Process Report: AI-Powered Intelligent Document Processing & QR-Based Automation

## 1. Executive Summary & Goal
EFL Global processes a massive volume of containers daily, each accompanied by a Gate Pass and supporting documents (Invoices, Packing Lists, Customs Documents, etc.). Currently, these documents are manually processed, leading to incorrect document ordering, misclassification, inconsistent folder naming, and lack of searchable metadata.

This project will build an **AI-Powered Intelligent Document Processing (IDP) Platform** to automate the complete lifecycle of warehouse document processing. This major architectural upgrade introduces a **QR Code-Based Gate Pass Processing layer**. The AI Agent will automatically detect, read, and validate QR codes on Gate Passes, utilizing the QR data as the digital key that connects physical warehouse documents to the enterprise system. This guarantees near-perfect accuracy in container matching, automated folder generation, and real-time website synchronization.

## 2. Proposed Architecture & Tech Stack
The system is built using Python and structured as a FastAPI + LangGraph application, orchestrated as specialized AI micro-agents operating as a state machine.

### Core Technologies
- **Backend & API**: FastAPI (Python)
- **AI Orchestration**: LangGraph Agent (State Machine Logic)
- **QR Detection & Decoding**: OpenCV, ZBar / ZXing
- **AI Vision Fallback**: GPT-4o Vision / Azure AI Vision
- **Core OCR & Classification**: Azure Document Intelligence
- **Database**: PostgreSQL (JSONB columns for metadata)
- **Storage**: Azure Blob Storage

## 3. Implementation Workflow & Application Structure

### Enterprise Infrastructure & Config
- **Containerization**: Managed via `docker-compose.yml` for local development (PostgreSQL, FastAPI).
- **Storage Strategy**: Sequenced PDFs and `QR_Metadata.json` are stored in Azure Blob Storage.
- **Monitoring & Telemetry**: Application Insights / Prometheus for tracking agent success rates and API latencies.

### AI Agents & Orchestration (LangGraph)
The core logic is divided into three functional phases governed by LangGraph:
1. **Ingestion & QR Processing (`src/agents/intake_agent.py`, `src/agents/qr_agent.py`)**
   - Monitors scanner output folders and batches new PDFs.
   - Detects the QR region, decodes data, and validates the JSON schema. Falls back to GPT-4o Vision if local QR reading fails.
2. **Validation, External Sync & NLP Classification (`src/agents/validation_agent.py`, `src/agents/classification_agent.py`)**
   - Cross-references the QR payload against standard OCR extraction and existing database records.
   - Performs **WMS/ERP data validation** to ensure the Container ID is expected and active.
   - Uses Azure Document Intelligence to classify all supporting pages (Invoice, Packing List, etc.) and strictly sequences them behind the Gate Pass.
3. **Folder Management, Storage & Exception Handling (`src/agents/folder_engine.py`)**
   - Creates structured document folders using a highly specific naming convention to prevent collisions on high-volume days: `YYYY-MM-DD_Container-[ContainerNumber]_GP-[GatePassID]/`.
   - Saves `QR_Metadata.json` and linked, sequenced documents (`01_GatePass.pdf`, `02_Invoice.pdf`, etc.) to Azure Blob Storage.
   - **Exception Management (DLQ)**: Routes documents that fail detection or validation to a Dead-Letter Queue for Human-in-the-loop (HITL) review.

### Website REST API & Frontend UI Integration (`src/api/routes.py`)
- Provides REST APIs in FastAPI to sync data with the EFL Portal.
- **Frontend UI Components**: Requires building a Master Data Grid (Dashboard), a **Folder Explorer View with Search Bar** (allows users to search by date/container details to find and open the system-generated folders like `YYYY-MM-DD_Container-[ContainerNumber]_GP-[GatePassID]/`), a Document Workspace (PDF viewer + metadata), and an Exception Dashboard for the DLQ.
- **AI Assistance Chat Bot**: An integrated chatbot on the website that is linked to all system features. Users can ask questions to get information about the IDP system or query specific document statuses.
- **Security**: Implements JWT/OAuth2 authentication to secure sensitive endpoints.
- Webhooks / REST endpoints ensure documents can be queried via perfect metadata seconds after scanning.

## 4. Implementation Roadmap & Task List

- [ ] **Phase 1: Requirements Analysis & Infrastructure Setup**
  - [x] Analyze v5.1 Architecture Report
  - [x] Establish Implementation Plan and Architecture Design
- [ ] **Phase 2: Solution Architecture & System Design**
  - [ ] Set up `docker-compose.yml` (PostgreSQL, FastAPI)
  - [ ] Initialize basic project structure (`src/main.py`, `src/database/`, `src/agents/`)
  - [ ] Update `requirements.txt` with OpenCV, ZBar, Azure AI, LangGraph, etc.
- [ ] **Phase 3: OCR, QR Code Engine & Document Processing Prototype**
  - [ ] Implement `src/agents/splitter_agent.py` (PDF batch splitting logic)
  - [ ] Implement `src/agents/qr_agent.py` (QR reading and JSON validation)
  - [ ] Implement `src/agents/classification_agent.py` (Azure Document Intelligence)
- [ ] **Phase 4: AI Agent Development (LangGraph Orchestration & FastApi)**
  - [ ] Implement `src/agents/intake_agent.py` (Scanner input simulation)
  - [ ] Implement `src/agents/validation_agent.py` (Cross-reference and WMS/ERP sync logic)
  - [ ] Build the LangGraph state machine (`src/agents/graph.py`)
  - [ ] Implement Dead-Letter Queue (DLQ) / Exception routing in graph
- [ ] **Phase 5: Folder Management, Sequence Logic & Blob Storage integration**
  - [ ] Implement `src/agents/folder_engine.py` (Generate date-based folders)
  - [ ] Integrate with Azure Blob Storage
- [ ] **Phase 6: Website REST API, Security & Frontend UI Integration**
  - [ ] Create secured API routes in `src/api/routes.py` (JWT/OAuth2)
  - [ ] Implement Webhook/REST sync for the EFL portal connection
  - [ ] Frontend: Develop Container Dashboard (Master Data Grid)
  - [ ] Frontend: Develop Folder Explorer View with Search Bar (Search by date/container to find and open specific container folders)
  - [ ] Frontend: Develop Document Workspace (Detail View with embedded PDF viewer)
  - [ ] Frontend: Develop Exception Dashboard (HITL interface for DLQ)
  - [ ] Frontend & Backend: Integrate AI Assistance Chat Bot (System-aware RAG bot to answer user queries and interact with system features)
- [ ] **Phase 7: User Acceptance Testing (UAT) & Performance Testing**
  - [ ] Run test batches to verify folder creation and sequencing
  - [ ] Perform load testing for high-volume scanner ingestion
- [ ] **Phase 8: Production Deployment, Training & Continuous Monitoring**
  - [ ] Finalize deployment configurations
  - [ ] Set up Application Insights / Telemetry for monitoring agent performance
