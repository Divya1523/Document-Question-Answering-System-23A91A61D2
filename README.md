**Gemini Document Q&A System (RAG with Batched API Calls)**

A fully containerized Retrieval-Augmented Generation (RAG) system that allows users to upload documents and ask questions grounded in the document content using Google Gemini API. The system supports asynchronous document processing, batched LLM calls for cost efficiency, conversational memory, token usage tracking, and PDF export of chat sessions.

**Features**

Upload PDF, TXT, DOCX documents
Asynchronous document parsing & chunking
Keyword-based chunk retrieval (no vector DB required)
Gemini-powered question answering (batched calls)
Token usage tracking per request
Conversation session memory
Export conversation to PDF
Fully containerized with Docker Compose
Clean Streamlit UI

**Architecture**

Frontend (Streamlit)  →  Backend (FastAPI)  →  Google Gemini API
                               |
                        Async document processing
                               |
                         Chunk storage in memory

**Project Structure**

.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── README.md

**Architecture Diagram**

┌────────────────────┐
│   User (Browser)   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Stream lit Frontend│
│      (UI Service)  │
└─────────┬──────────┘
          │ HTTP Requests
          ▼
┌──────────────────────────────────┐
│        FastAPI Backend           │
│          (API Service)           │
│                                  │
│  ┌───────────────┐               │
│  │ Upload Docs   │               │
│  │ Async Parsing │               │
│  │ Chunking      │               │
│  └───────────────┘               │
│                                  │
│  ┌───────────────┐               │
│  │ Keyword       │
│  │ Retrieval     │
│  └───────────────┘               │
│                                  │
│  ┌───────────────┐               │
│  │ Batched Prompt│──────────────▶│ Google Gemini API
│  │ Generation    │               │ (LLM Service)
│  └───────────────┘               │
│                                  │
│  ┌───────────────┐               │
│  │ Session Memory│               │
│  │ Token Tracking│               │
│  │ PDF Export    │               │
│  └───────────────┘               │
└──────────────────────────────────┘

**Mermaid Diagram**

graph TD
    U[User Browser] --> UI[Streamlit Frontend]

    UI --> API[FastAPI Backend]

    API -->|Upload| P[Async Document Processing]
    P --> C[Text Chunking]

    API --> R[Keyword Retrieval]
    R --> B[Batched Prompt Builder]

    B --> G[Google Gemini API]

    G --> API

    API --> S[Session Memory]
    API --> T[Token Tracking]
    API --> PDF[PDF Export]

    API --> UI

**Run the Application**

Make sure Docker Desktop is running.
docker-compose up --build

Access:
Backend API:
http://localhost:8000

Frontend UI:
http://localhost:8501

**Technology Stack**

Layer	         |   Technology

Backend	         |   FastAPI
Frontend	     |  Streamlit
LLM	             |  Google Gemini API
Containerization |	Docker + Docker Compose
PDF Generation	 |  ReportLab

**Implementation Notes**

No vector database used (keyword retrieval as per spec)
Async processing with FastAPI BackgroundTasks
Batched Gemini prompts for cost efficiency
In-memory storage (simple & sufficient for task)
Token usage captured per request
Service-to-service networking via Docker


