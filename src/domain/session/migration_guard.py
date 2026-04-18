"""
Schema migration guard for session persistence.

Ensures that database schema matches the expected session persistence structure
and performs necessary validation before operations.
"""

import logging
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session as SQLSession

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    pass


class SessionSchemaMigrationGuard:
    """
    Validates and enforces session persistence schema consistency.
    
    Performs checks on:
    - cv_sessions table existence and structure
    - Column types and constraints
    - Index definitions
    - Data integrity
    """

    # Expected cv_sessions table schema
    EXPECTED_COLUMNS = {
        "session_id": "VARCHAR(64)",
        "canonical_cv": "TEXT",
        "validation_results": "TEXT",
        "status": "VARCHAR(32)",
        "created_at": "DATETIME",
        "last_updated_at": "DATETIME",
        "exported_at": "DATETIME",
        "expires_at": "DATETIME",
        "source_history": "TEXT",
        "uploaded_artifacts": "TEXT",
        "metadata": "TEXT",
        "workflow_state": "TEXT",
        "version": "INTEGER",
    }

    REQUIRED_INDEXES = {
        "ix_cv_sessions_expires_at": ["expires_at"],
        "ix_cv_sessions_status": ["status"],
    }

    PRIMARY_KEY = "session_id"

    @classmethod
    def validate_schema(cls, db: SQLSession) -> bool:
        """
        Validate that cv_sessions table exists with correct schema.
        
        Returns:
            True if schema is valid
            
        Raises:
            SchemaValidationError if validation fails
        """
        logger.info("Starting session schema validation...")
        
        # Check table existence
        if not cls._table_exists(db):
            logger.error("cv_sessions table does not exist")
            raise SchemaValidationError("cv_sessions table not found in database")
        
        # Check columns
        missing_columns = cls._check_columns(db)
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            raise SchemaValidationError(f"Missing required columns in cv_sessions: {missing_columns}")
        
        # Check indexes
        missing_indexes = cls._check_indexes(db)
        if missing_indexes:
            logger.warning(f"Missing indexes: {missing_indexes}. Performance may be impacted.")
        
        # Check primary key
        if not cls._check_primary_key(db):
            logger.error("Primary key constraint missing or incorrect")
            raise SchemaValidationError("cv_sessions table missing or invalid primary key")
        
        logger.info("Session schema validation passed")
        return True

    @classmethod
    def _table_exists(cls, db: SQLSession) -> bool:
        """Check if cv_sessions table exists."""
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        return "cv_sessions" in tables

    @classmethod
    def _check_columns(cls, db: SQLSession) -> list[str]:
        """Check for missing or incorrect columns."""
        inspector = inspect(db.get_bind())
        existing_columns = {col["name"] for col in inspector.get_columns("cv_sessions")}
        expected_columns = set(cls.EXPECTED_COLUMNS.keys())
        
        missing = expected_columns - existing_columns
        return list(missing)

    @classmethod
    def _check_indexes(cls, db: SQLSession) -> list[str]:
        """Check for missing or incorrect indexes."""
        inspector = inspect(db.get_bind())
        existing_indexes = {idx["name"]: idx["column_names"] for idx in inspector.get_indexes("cv_sessions")}
        
        missing = []
        for index_name, columns in cls.REQUIRED_INDEXES.items():
            if index_name not in existing_indexes:
                missing.append(index_name)
            elif existing_indexes[index_name] != columns:
                logger.warning(f"Index {index_name} has different columns than expected")
        
        return missing

    @classmethod
    def _check_primary_key(cls, db: SQLSession) -> bool:
        """Check for correct primary key."""
        inspector = inspect(db.get_bind())
        pk_constraint = inspector.get_pk_constraint("cv_sessions")
        return pk_constraint and cls.PRIMARY_KEY in pk_constraint.get("constrained_columns", [])

    @classmethod
    def ensure_schema_initialized(cls, db: SQLSession) -> None:
        """
        Ensure schema is initialized. If table doesn't exist, create it.
        
        This is called on application startup to guarantee schema exists.
        """
        if not cls._table_exists(db):
            logger.warning("cv_sessions table not found. Creating schema...")
            cls._create_schema(db)
        
        try:
            cls.validate_schema(db)
        except SchemaValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise

    @classmethod
    def _create_schema(cls, db: SQLSession) -> None:
        """Create cv_sessions table if it doesn't exist."""
        ddl = text(
            """
            CREATE TABLE IF NOT EXISTS cv_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                canonical_cv LONGTEXT NOT NULL,
                validation_results LONGTEXT NOT NULL,
                status VARCHAR(32) NOT NULL,
                created_at DATETIME NOT NULL,
                last_updated_at DATETIME NOT NULL,
                exported_at DATETIME,
                expires_at DATETIME NOT NULL,
                source_history LONGTEXT NOT NULL,
                uploaded_artifacts LONGTEXT NOT NULL,
                metadata LONGTEXT NOT NULL,
                workflow_state LONGTEXT NOT NULL,
                version INT NOT NULL DEFAULT 1,
                INDEX ix_cv_sessions_expires_at (expires_at),
                INDEX ix_cv_sessions_status (status)
            )
            """
        )
        try:
            db.execute(ddl)
            db.commit()
            logger.info("cv_sessions table created successfully")
        except Exception as e:
            logger.error(f"Failed to create cv_sessions table: {e}")
            db.rollback()
            raise


class SessionDataIntegrityValidator:
    """Validates data integrity of persisted sessions."""

    @classmethod
    def validate_session_record(cls, session_record: dict) -> bool:
        """
        Validate a session record for data integrity.
        
        Checks:
        - Required fields are present
        - Session ID is non-empty
        - Timestamps are valid
        - Version is positive
        - JSON fields are valid
        
        Returns:
            True if record is valid
            
        Raises:
            ValueError if record is invalid
        """
        required_fields = [
            "session_id",
            "canonical_cv",
            "validation_results",
            "status",
            "created_at",
            "last_updated_at",
            "expires_at",
            "source_history",
            "uploaded_artifacts",
            "metadata",
            "workflow_state",
            "version",
        ]
        
        # Check required fields
        missing_fields = [f for f in required_fields if f not in session_record]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Validate session ID
        if not session_record["session_id"] or not isinstance(session_record["session_id"], str):
            raise ValueError("session_id must be a non-empty string")
        
        # Validate version
        if not isinstance(session_record["version"], int) or session_record["version"] < 1:
            raise ValueError("version must be a positive integer")
        
        # Validate status
        valid_statuses = {"active", "exported", "deleted"}
        if session_record["status"].lower() not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        
        # Validate timestamps
        try:
            created = session_record["created_at"]
            updated = session_record["last_updated_at"]
            expires = session_record["expires_at"]
            
            if not isinstance(created, datetime):
                raise ValueError("created_at must be a datetime")
            if not isinstance(updated, datetime):
                raise ValueError("last_updated_at must be a datetime")
            if not isinstance(expires, datetime):
                raise ValueError("expires_at must be a datetime")
            
            if updated < created:
                raise ValueError("last_updated_at cannot be before created_at")
        except (AttributeError, TypeError) as e:
            raise ValueError(f"Timestamp validation failed: {e}")
        
        logger.info(f"Session record {session_record['session_id']} passed integrity validation")
        return True

    @classmethod
    def repair_corrupted_json_field(cls, value: str, field_name: str) -> dict:
        """
        Attempt to repair corrupted JSON field.
        
        Returns:
            Parsed JSON if repair succeeds, empty dict otherwise
        """
        import json
        
        if not value:
            logger.warning(f"Empty {field_name}, returning empty dict")
            return {}
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {field_name}: {e}. Returning empty dict.")
            return {}
