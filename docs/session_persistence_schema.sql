-- Session persistence schema for production relational databases.
-- Use PostgreSQL JSONB where available; in MySQL use JSON columns.

CREATE TABLE cv_sessions (
    session_id            VARCHAR(64) PRIMARY KEY,
    canonical_cv          JSON NOT NULL,
    validation_results    JSON NOT NULL,
    status                VARCHAR(20) NOT NULL,
    source_history        JSON NOT NULL,
    uploaded_artifacts    JSON NOT NULL,
    metadata              JSON NOT NULL,
    version               INTEGER NOT NULL DEFAULT 1,
    created_at            TIMESTAMP NOT NULL,
    last_updated_at       TIMESTAMP NOT NULL,
    exported_at           TIMESTAMP NULL,
    expires_at            TIMESTAMP NOT NULL
);

CREATE INDEX idx_cv_sessions_status ON cv_sessions (status);
CREATE INDEX idx_cv_sessions_expires_at ON cv_sessions (expires_at);
CREATE INDEX idx_cv_sessions_last_updated_at ON cv_sessions (last_updated_at DESC);

-- Optional normalized event table for high-volume audit reporting.
CREATE TABLE cv_session_events (
    event_id              BIGSERIAL PRIMARY KEY,
    session_id            VARCHAR(64) NOT NULL,
    source_type           VARCHAR(40) NOT NULL,
    description           VARCHAR(255) NOT NULL,
    payload_metadata      JSON NOT NULL,
    event_at              TIMESTAMP NOT NULL,
    CONSTRAINT fk_cv_session_events_session
        FOREIGN KEY (session_id) REFERENCES cv_sessions(session_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_cv_session_events_session_id ON cv_session_events (session_id);
CREATE INDEX idx_cv_session_events_event_at ON cv_session_events (event_at DESC);
