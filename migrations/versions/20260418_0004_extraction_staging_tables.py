"""
add extraction staging tables

Revision ID: 20260418_0004
Revises: 20260418_0003
Create Date: 2026-04-18 10:00:00.000000

Adds canonical extraction staging layer for data persistence and traceability:
- cv_extraction_staging: Main staging table for all extracted CV data
- cv_extraction_field_confidence: Field-level extraction confidence tracking
"""

from alembic import op
import sqlalchemy as sa


revision = "20260418_0004"
down_revision = "20260418_0003"
branch_labels = None
depends_on = None


def upgrade():
    """Create extraction staging tables"""
    
    # Create cv_extraction_staging table
    op.create_table(
        'cv_extraction_staging',
        sa.Column('extraction_id', sa.String(64), nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('source_filename', sa.String(255), nullable=True),
        sa.Column('source_size_bytes', sa.Integer, nullable=True),
        sa.Column('raw_extracted_text', sa.Text, nullable=True),
        sa.Column('normalized_text', sa.Text, nullable=True),
        sa.Column('parsed_intermediate', sa.JSON, nullable=True),
        sa.Column('canonical_cv', sa.JSON, nullable=True),
        sa.Column('field_confidence', sa.JSON, nullable=True),
        sa.Column('extraction_warnings', sa.JSON, nullable=True),
        sa.Column('extraction_errors', sa.JSON, nullable=True),
        sa.Column('extraction_status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('extracted_at', sa.DateTime, nullable=True),
        sa.Column('previewed_at', sa.DateTime, nullable=True),
        sa.Column('exported_at', sa.DateTime, nullable=True),
        sa.Column('cleared_at', sa.DateTime, nullable=True),
        sa.Column('llm_enhancement_applied', sa.String(32), nullable=False, server_default='none'),
        sa.Column('llm_confidence_score', sa.Float, nullable=True),
        sa.PrimaryKeyConstraint('extraction_id'),
    )
    
    # Create indexes
    op.create_index('ix_extraction_staging_extraction_id', 'cv_extraction_staging', ['extraction_id'], unique=True)
    op.create_index('ix_extraction_staging_session', 'cv_extraction_staging', ['session_id'])
    op.create_index('ix_extraction_staging_status', 'cv_extraction_staging', ['extraction_status'])
    op.create_index('ix_extraction_staging_created', 'cv_extraction_staging', ['created_at'])
    
    # Create cv_extraction_field_confidence table
    op.create_table(
        'cv_extraction_field_confidence',
        sa.Column('extraction_id', sa.String(64), sa.ForeignKey('cv_extraction_staging.extraction_id'), nullable=False),
        sa.Column('field_path', sa.String(128), nullable=False),
        sa.Column('extraction_method', sa.String(64), nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('extracted_value', sa.Text, nullable=True),
        sa.Column('normalized_value', sa.Text, nullable=True),
        sa.Column('validation_status', sa.String(32), nullable=False, server_default='unknown'),
        sa.Column('extraction_notes', sa.Text, nullable=True),
        sa.Column('fallback_used', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('extraction_id', 'field_path'),
    )
    
    # Create index
    op.create_index('ix_field_confidence_extraction', 'cv_extraction_field_confidence', ['extraction_id'])


def downgrade():
    """Drop extraction staging tables"""
    
    # Drop indexes
    op.drop_index('ix_field_confidence_extraction', table_name='cv_extraction_field_confidence')
    op.drop_index('ix_extraction_staging_created', table_name='cv_extraction_staging')
    op.drop_index('ix_extraction_staging_status', table_name='cv_extraction_staging')
    op.drop_index('ix_extraction_staging_extraction_id', table_name='cv_extraction_staging')
    op.drop_index('ix_extraction_staging_session', table_name='cv_extraction_staging')
    
    # Drop tables
    op.drop_table('cv_extraction_field_confidence')
    op.drop_table('cv_extraction_staging')
