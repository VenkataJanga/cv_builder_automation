# Conversational CV Builder — Solution Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              EXPERIENCE LAYER                                │
│         Web UI         Chat Interface  |  Live Audio  |  Upload Audio        │
│  Upload DOC/DOCX/PDF  |  Preview  |  Export  |  Future API Integrations      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                   API LAYER                                  │
│                    FastAPI Application / REST Endpoints                      │
│          Session  |  Conversation  |  Upload  |  Preview  |  Export          │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW / ORCHESTRATION LAYER                       │
│                      LangGraph-style Stateful Workflow                       │
│     Role Resolution  |  Question Flow  |  Follow-up Branching  |  Edit Loop  │
│           Parse  →  Enrich  →  Validate  →  Preview  →  Export               │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION / SERVICE LAYER                          │
│  Conversation Service   |   CV Builder Service   |   Questionnaire Service   │
│  Retrieval Service      |   Validation Service   |   Export Service          │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN / CONTROL LAYER                            │
│                          Canonical CV Schema                                 │
│  Personal Details | Summary | Skills | Work Experience | Projects            │
│  Certifications   | Education | Languages | Validation Metadata              │
│                                                                              │
│  Merge Rules: user-confirmed input wins                                      │
│  Validation Rules: completeness / chronology / formatting / readiness        │
└──────────────────────────────────────────────────────────────────────────────┘
                    │                           │                           │
                    ▼                           ▼                           ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐
│        PARSING LAYER        │   │          AI LAYER           │   │      RETRIEVAL LAYER        │
│ DOCX Extractor              │   │ LLM Provider Layer          │   │ Indexing Pipeline           │
│ PDF Extractor               │   │ OpenAI (Dev)                │   │ Chunking / Metadata         │
│ Audio Transcript Handling   │   │ Azure OpenAI (Prod Ready)   │   │ Embeddings / Language Tags  │
│ Resume Parser               │   │ Extraction Agent            │   │ Contextual / Hybrid Retrieve│
│ LLM-assisted Normalization  │   │ Enhancement Agent           │   │ FAISS (Dev)                 │
│ Field Extraction            │   │ Summarization Agent         │   │ Azure AI Search (Future)    │
│                             │   │ Validation Agent            │   │ Knowledge Sources           │
│                             │   │ Prompt Layer + Guardrails   │   │ CV rules / skills /templates│
└─────────────────────────────┘   └─────────────────────────────┘   └─────────────────────────────┘
                    │                           │                           │
                    └───────────────┬───────────┴───────────────┬───────────┘
                                    ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       PREVIEW / TEMPLATE / EXPORT LAYER                      │
│     Template Engine  |  Live Preview  |  DOCX Renderer  |  PDF Renderer      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     PERSISTENCE / INFRASTRUCTURE LAYER                       │
│  MySQL: Users / Sessions / CV Records / Validation / Audit                   │
│  File Storage: Local FS (Current) / Azure ADLS (Future)                      │
│  Observability: Logging / Tracing / App Insights / LangSmith                 │
│  Security: Current Auth / Entra ID + RBAC (Future)                           │
└──────────────────────────────────────────────────────────────────────────────┘
```