# AI-Powered Intelligent Document Processing (IDP) Platform

![EFL Global IDP](https://img.shields.io/badge/EFL%20Global-IDP-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Azure](https://img.shields.io/badge/azure-%230072C6.svg?style=for-the-badge&logo=microsoftazure&logoColor=white)

EFL Global processes a massive volume of containers daily, each accompanied by a Gate Pass and supporting documents (Invoices, Packing Lists, Customs Documents, etc.). This project automates the complete lifecycle of warehouse document processing using an advanced AI architecture.

By introducing a **QR Code-Based Gate Pass Processing layer**, the AI Agent automatically detects, reads, and validates QR codes on Gate Passes, utilizing the QR data as the digital key that connects physical warehouse documents to the enterprise system. This guarantees near-perfect accuracy in container matching, automated folder generation, and real-time website synchronization.

## 🚀 Features

*   **Intelligent PDF Splitting**: Automatically handles bulk scanner outputs, splitting massive PDFs into logical container batches using computer vision.
*   **QR Code Extraction**: High-speed, offline-capable QR code detection using `pyzbar` and `OpenCV`.
*   **AI Orchestration with LangGraph**: A robust state-machine governing document intake, validation, exception handling, and storage.
*   **WMS/ERP Validation**: Real-time cross-referencing with the central Warehouse Management System to verify active containers.
*   **Azure Document Intelligence Integration**: Cloud-based NLP for classifying and extracting data from supporting documents (Invoices, Packing Lists).
*   **Dead-Letter Queue (DLQ)**: Human-in-the-loop exception management for failed or unreadable documents.
*   **Premium Web Portal**: A React/Next.js frontend featuring a Folder Explorer, Container Dashboard, and an integrated **AI Assistant Chatbot**.

## 🏗️ Architecture

The system is built as a highly scalable micro-agent architecture:

*   **Backend API**: FastAPI
*   **Database**: PostgreSQL (JSONB schema) & Redis (Task queues)
*   **AI Agents**: Python (LangGraph)
*   **Storage**: Azure Blob Storage
*   **Deployment**: Docker & Docker Compose

### Folder Organization Logic

To prevent collisions on high-volume days and guarantee exact sequencing, the system strictly generates folders as follows:
`YYYY-MM-DD_Container-[ContainerNumber]_GP-[GatePassID]/`

Inside, documents are named chronologically:
1.  `01_GatePass.pdf`
2.  `02_Invoice.pdf`
3.  `...`
4.  `QR_Metadata.json`

## 🛠️ Local Setup (Docker)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Thasmika/AI-Powered-Intelligent-Document-Processing-IDP-Platform.git
   cd AI-Powered-Intelligent-Document-Processing-IDP-Platform
   ```

2. **Start the infrastructure:**
   ```bash
   docker-compose up -d --build
   ```
   This will spin up PostgreSQL, Redis, and the FastAPI application on `http://localhost:8000`.

3. **Check the API Health:**
   Navigate to `http://localhost:8000/health` or view the Swagger UI at `http://localhost:8000/docs`.

## 📜 Documentation

For more in-depth architectural details, please refer to:
*   [Technical Process Report](Technical_Process_Report.md)
*   [Implementation Plan](implementation_plan.md)
*   [Task List](task%20list.md)

---
*Built for EFL Global.*