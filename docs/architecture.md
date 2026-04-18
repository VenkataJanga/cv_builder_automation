# Architecture Overview

This document describes the current architecture of the Conversational CV Builder repository as implemented today.

## Layered Architecture

### Client Layer
- `web-ui/index.html`, `web-ui/app.js`
- Browser-based web UI for chat, audio upload, preview, and export
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

### Configuration
- Default backend is `memory`.
- `src/application/services/conversation_service.py` selects the session repository backend using `SESSION_REPOSITORY_BACKEND`.
- `SESSION_REPOSITORY_BACKEND=mysql` enables MySQL-backed session persistence.
- `.env.example` is already configured to use `mysql` for durable session persistence in development.
- Otherwise the application uses `InMemorySessionRepository`, and session data is lost when the server restarts.

### Persistence Layer
- `src/domain/session/service.py`: `SessionService` provides atomic multi-field updates via `save_workflow_state()`
- `src/domain/session/repositories.py`: Three backends support different deployment scenarios:
  - `DatabaseSessionRepository`: MySQL-backed (production)
  - `InMemorySessionRepository`: Fast in-memory (development/testing)
  - `FileSessionRepository`: JSON file-based (debugging)
- `src/domain/session/models.py`: `CVSession` model tracks 8 core fields:
  - `canonical_cv`: Canonical CV schema (persisted JSON)
  - `validation_results`: Validation output (persisted JSON)
  - `workflow_state`: UI workflow state (step, role, answers, etc.)
  - `source_history`: Immutable audit trail of all changes
  - `uploaded_artifacts`: File metadata tracking
  - `metadata`: User/tenant context
  - `status`: Session lifecycle (active/exported/expired)
  - `version`: Optimistic locking for concurrent safety

### Schema Evolution & Startup Validation
- `apps/api/main.py` calls `ensure_schema_initialized()` on every application startup
- `src/domain/session/migration_guard.py`: 
  - `SessionSchemaMigrationGuard` validates `cv_sessions` table structure (13 columns + 2 indexes)
  - `SessionDataIntegrityValidator` performs record-level integrity checks and repairs
  - Application fails fast if schema is invalid (preventing silent data loss)
- The MySQL table `cv_sessions` exists in migrations with 13 columns indexed for performance

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

---

## NEW: Extraction Staging Layer (April 2026)

### Overview
Canonical CV extraction data now persists through a dedicated staging layer to ensure **zero data loss** and **complete traceability** across all input channels.

### Staging Infrastructure

#### Database Layer
Two new MySQL tables in `migrations/versions/20260418_0004_extraction_staging_tables.py`:

**`cv_extraction_staging` (22 columns)**
- `extraction_id` (PK): Unique extraction identifier (UUID)
- `session_id` (FK): User session for cross-reference
- `source_type`: enum(document_upload, audio_upload, conversation)
- **Extraction pipeline outputs**:
  - `raw_extracted_text`: Text before normalization
  - `normalized_text`: After cleanup/normalization
  - `parsed_intermediate` (JSON): Intermediate parsed structure before schema mapping
  - `canonical_cv` (JSON): Final mapped canonical CV schema
- **Quality tracking**:
  - `field_confidence` (JSON): Per-field confidence scores (0.0-1.0)
  - `extraction_warnings`: List of warnings from extraction process
  - `extraction_errors`: List of recoverable errors
- **Lifecycle tracking**:
  - `extraction_status`: pending → in_progress → complete → previewed → exported → cleared
  - `created_at`, `updated_at`: Timestamps
  - `extracted_at`, `previewed_at`, `exported_at`, `cleared_at`: Stage-specific timestamps
- **LLM metadata**:
  - `llm_enhancement_applied`: none, hybrid, full_llm
  - `llm_confidence_score`: Overall LLM confidence (if applicable)

**`cv_extraction_field_confidence` (field-level details)**
- `extraction_id` (FK): Reference to extraction_staging
- `field_path`: Field identifier (e.g., "candidate.fullName", "skills.technicalSkills")
- `extraction_method`: deterministic, regex, llm, fallback, default
- `confidence_score`: 0.0-1.0 per field
- `extracted_value`, `normalized_value`: Raw and normalized values
- `validation_status`: unknown, valid, questionable, invalid, required_missing
- `extraction_notes`: Why this method was chosen
- `fallback_used`: Which fallback strategy was applied

#### Service Layer
**`CanonicalDataStagingService`** (`src/domain/cv/services/canonical_data_staging_service.py`)

Methods for extraction lifecycle:
- `create_extraction_record()`: Initialize staging with metadata
- `stage_raw_extraction()`: Persist raw and normalized text
- `stage_parsed_intermediate()`: Store parsed structure before mapping
- `stage_canonical_and_confidence()`: Persist final canonical CV with field scores
- `mark_previewed()`: Record when preview generated
- `mark_exported()`: Record when export completed
- `clear_session_staging()`: Mark records as cleared (not deleted)
- `get_extraction_record()`: Retrieve staging metadata
- `get_canonical_cv_from_staging()`: Get canonical CV by session or extraction ID
- `get_extraction_history()`: Retrieve extraction history (reverse chronological)
- `get_field_confidence_report()`: Detailed field-level confidence data

### Integration Points

#### 1. DocumentCVService
```python
def process_document_upload(self, session_id, file_path, file_metadata):
    # Step 0: Create staging record
    extraction_id = staging_service.create_extraction_record(...)
    
    # Step 1: Extract raw text
    raw_text = parser.extract_text(file_path)
    staging_service.stage_raw_extraction(extraction_id, raw_text)
    
    # Step 2: Parse to canonical
    canonical = parser.parse_document_to_canonical(...)
    
    # Step 3: Stage canonical + confidence
    staging_service.stage_canonical_and_confidence(
        extraction_id, canonical, 
        field_confidence=_calculate_field_confidence(canonical)
    )
    
    return {"canonical_cv": canonical, "extraction_id": extraction_id}
```

#### 2. PreviewService
```python
def build_preview_from_staging(self, session_id, extraction_id=None):
    # Retrieve from persistent staging layer
    canonical = staging_service.get_canonical_cv_from_staging(session_id, extraction_id)
    
    # Mark as previewed for audit trail
    staging_service.mark_previewed(extraction_id)
    
    # Generate preview
    return formatter.format_cv(canonical)
```

#### 3. ExportService
```python
def export_docx(self, cv_data):
    # Generate export
    docx_bytes = renderer.render(cv_data)
    
    # Mark as exported in staging
    export_service.mark_extraction_exported(extraction_id)
    
    # Optional: Clear staging after successful export
    export_service.clear_session_staging_after_export(session_id)
    
    return docx_bytes
```

#### 4. ConversationService
```python
def reset_session(self, session_id):
    # Clear extraction staging on logout
    staging_service.clear_session_staging(session_id)
    
    # Delete session
    repository.delete_session(session_id)
```

### Extraction Lifecycle

```
User Action                 Staging State              Database Record
─────────────────────────────────────────────────────────────────────────
1. Upload CV          →    PENDING                  extraction_id created
                           (record initialized)      source_type, filename stored

2. Extract Text       →    IN_PROGRESS              raw_extracted_text persisted
                           (raw text staged)        normalized_text persisted

3. Parse to Canonical →    IN_PROGRESS              parsed_intermediate persisted
                           (parsed intermediate)    warnings/errors stored

4. Map to Schema      →    COMPLETE                 canonical_cv persisted
                           (final output)           field_confidence scores stored
                                                    extracted_at timestamp set
                                                    llm_metadata recorded

5. Generate Preview   →    PREVIEWED                previewed_at timestamp set
                           (audit trail update)     extraction_status = previewed

6. Export to PDF/DOC  →    EXPORTED                 exported_at timestamp set
                           (audit trail update)     extraction_status = exported

7. Session Reset      →    CLEARED                  cleared_at timestamp set
                           (cleanup)                extraction_status = cleared
                           (records NOT deleted)    (audit trail preserved)
```

### Field Confidence Calculation

Automatic scoring based on data presence and extraction method:

```python
# High confidence (0.85-0.95)
- Full Name extracted deterministically: 0.95
- Email/Phone extracted deterministically: 0.95
- Current Designation extracted: 0.90

# Medium-high confidence (0.70-0.85)
- Skills extracted from section: 0.85
- Experience items extracted: 0.80
- Projects extracted: 0.75

# Medium confidence (0.50-0.70)
- Education extracted: 0.70
- Certifications extracted: 0.65
- Extracted via fallback method: 0.55

# Low confidence (< 0.50)
- Missing required fields: 0.20
- Extracted via LLM only (no deterministic method): 0.40
```

### Zero Data Loss Guarantee

1. **Raw text persisted immediately** after extraction (before any processing)
2. **Normalized text persisted** before parsing (prevents loss if parser fails)
3. **Intermediate parsed structure persisted** before schema mapping
4. **Final canonical CV persisted** with full field confidence
5. **Records never deleted** (marked as "cleared" for audit compliance)
6. **Complete audit trail** of all stages in `updated_at` and stage-specific timestamps

### Traceability & Debugging

Field-level confidence report helps identify extraction gaps:
```sql
SELECT field_path, confidence_score, extraction_method, 
       extracted_value, validation_status
FROM cv_extraction_field_confidence
WHERE extraction_id = '...'
ORDER BY confidence_score ASC;
```

Can identify:
- Low-confidence fields requiring manual review
- Methods used for each field (deterministic vs fallback vs LLM)
- Validation status (valid, questionable, invalid, missing)
- Which fallback strategies worked vs failed

### Performance Impact

- Staging adds ~50-100ms per extraction (JSON serialization to DB)
- Retrieval from staging: <10ms (indexed lookups)
- No impact on preview/export (single query to get canonical CV)
- Minimal storage overhead (canonical_cv field already compressed)

### Migration & Deployment

Migration file: `migrations/versions/20260418_0004_extraction_staging_tables.py`

```bash
# Apply migration
alembic upgrade head

# Verify tables
mysql cv_builder -e "SHOW TABLES;" | grep extraction

# Check indexes
mysql cv_builder -e "SHOW INDEXES FROM cv_extraction_staging;"
```
