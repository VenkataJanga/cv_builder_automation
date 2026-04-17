# Architecture Overview

This document describes the current architecture of the Conversational CV Builder repository as implemented today.

## Layered Architecture

### Client Layer
- `demo-ui/index.html`, `demo-ui/app.js`
- Browser-based demo UI for chat, audio upload, preview, and export
- External API clients or integrations may call the same FastAPI endpoints

### Application Layer
- `apps/api/main.py`
- FastAPI server with routers for:
  - auth
  - chat
  - session
  - preview
  - export
  - CV upload
  - validation
  - retrieval
  - speech
  - questionnaire
  - templates
  - review
- Includes CORS middleware and auth middleware

### Business Logic Layer
- `src/application/services/conversation_service.py`
  - orchestrates conversational intake and session lifecycle
  - selects session persistence backend
- `src/application/services/cv_builder_service.py`
  - builds canonical CV schema
  - maps questionnaire answers into CV fields
- `src/application/services/validation_service.py`
  - validates completeness and export readiness
- `src/application/services/retrieval_service.py`
  - supports contextual retrieval for conversational responses
- `src/application/services/document_cv_service.py`
  - handles document upload, parsing, merge, and session updates
- `src/application/services/export_service.py`
  - renders DOCX/PDF exports using the template engine

### Questionnaire and Parsing
- `src/questionnaire/`
  - answer analysis
  - follow-up rules
  - question selection
  - role resolution
- `src/domain/cv/services/merge_cv.py`
  - merge logic for incoming CV data
- `src/ai/services/voice_transcript_*`
  - audio transcript parsing and canonical field extraction

### Orchestration Layer
- `src/orchestration/langgraph_workflows.py`
- `src/orchestration/langgraph_cv_workflow.py`
- `src/orchestration/enhanced_cv_orchestrator.py`
- `src/orchestration/workflows/`
- Defines a LangGraph-style workflow with:
  - `extract_text`
  - `hybrid_extraction`
  - `deep_validation`
  - `retrieval`
  - `enhancement`
  - `followup_generation`

### AI Layer
- `src/ai/providers/`
  - OpenAI provider wrappers
  - Azure OpenAI provider support
- `src/ai/services/`
  - enhancement agents
  - extraction agents
  - validation agents
  - summarization agents
- `config/prompts/`
  - extraction
  - enhancement
  - validation
  - summarization
- Guardrails are enforced through prompt design and validation logic

### Retrieval Layer
- `src/retrieval/indexing/index_service.py`
- `src/retrieval/retrievers/contextual_retriever.py`
- `src/retrieval/vectorstores/faiss_store.py`
- Current retrieval stack is a lightweight FAISS-compatible placeholder
- Supports embeddings, chunking, and top-k context lookup

### Infrastructure Layer
- `src/infrastructure/persistence/mysql/`
  - MySQL persistence models and repository support
- `src/infrastructure/rendering/template_engine.py`
  - preview/export rendering
- `data/storage/`
  - local file storage for uploads and artifacts
- `config/environments/`
  - runtime environment configuration
- `apps/worker/`
  - worker and job placeholder support

## Session Persistence Behavior

- Default backend is `memory`.
- `src/application/services/conversation_service.py` selects the session repository backend using `SESSION_REPOSITORY_BACKEND`.
- `SESSION_REPOSITORY_BACKEND=mysql` enables MySQL-backed session persistence.
- Otherwise the application uses `InMemorySessionRepository`, and session data is lost when the server restarts.
- The MySQL table `cv_sessions` exists in migrations, but it is only populated when the backend is configured to `mysql`.

## Primary User Flows

### Audio Upload Flow
1. Upload audio via `speech_router`
2. Transcribe audio with Whisper / speech provider
3. Parse transcript into canonical CV schema
4. Merge into session
5. Validate and persist session
6. Generate preview/export results

### Conversational Q&A Flow
1. Start or resume a session
2. Select next questions via the questionnaire engine
3. Process answers and update canonical CV
4. Validate and save session
5. Continue follow-up or complete the workflow

### Document Upload Flow
1. Upload DOCX/PDF via CV upload endpoints
2. Extract text
3. Parse into canonical schema
4. Merge with existing session
5. Validate and save

## Key Code References

- `apps/api/main.py`
- `src/application/services/conversation_service.py`
- `src/orchestration/langgraph_workflows.py`
- `src/core/config/settings.py`
- `src/interfaces/rest/routers/`
- `src/retrieval/`
- `src/infrastructure/persistence/mysql/`
