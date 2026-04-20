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

## Centralized Audit Logging

The application writes operational events to the `transaction_event_logs` table for traceability and support workflows.

- Auth events: login success and failure (`module_name=auth`, `operation=login`)
- API module events: chat, cv, speech, export flows
- Captured metadata includes actor, status, http_status, source_channel, payload, and timestamp

### Audit Query API

Use `GET /audit/events` to retrieve logs with filters.

- Access: `ADMIN` or `DELIVERY_MANAGER`
- Query params:
    - `limit` (1-500)
    - `module_name`
    - `operation`
    - `status`
    - `session_id`
    - `actor_username`
    - `created_from` (ISO datetime)
    - `created_to` (ISO datetime)

Example:

```bash
curl -X GET "http://localhost:8000/audit/events?module_name=auth&operation=login&status=failed&limit=50" \
    -H "Authorization: Bearer <token>"
```

### Admin Audit Dashboard (Lightweight)

Use the browser page below for quick filtering without writing SQL:

- URL: `/audit-dashboard.html`
- Data source: `GET /audit/events`
- Auth: paste a bearer token in the page, then click **Load Events**

### SQL Query Pack

For direct database reporting, use:

- `scripts/audit_queries.sql`

This query pack includes:

- latest login attempts
- failed logins in the last 24 hours
- user activity summaries
- module/operation breakdowns
- actor timeline
- session timeline
- hourly error trend
- top error messages