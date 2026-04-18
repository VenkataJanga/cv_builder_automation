"""Add transaction_event_logs table for module-level success/failure transaction logging

Revision ID: 20260418_0002
Revises: 20260416_0001
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260418_0002"
down_revision: Union[str, Sequence[str], None] = "20260416_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transaction_event_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("module_name", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_channel", sa.String(length=64), nullable=True),
        sa.Column("export_format", sa.String(length=16), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index(
        "ix_transaction_event_logs_session_id",
        "transaction_event_logs",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_event_logs_module_name",
        "transaction_event_logs",
        ["module_name"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_event_logs_status",
        "transaction_event_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_event_logs_created_at",
        "transaction_event_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_event_logs_created_at", table_name="transaction_event_logs")
    op.drop_index("ix_transaction_event_logs_status", table_name="transaction_event_logs")
    op.drop_index("ix_transaction_event_logs_module_name", table_name="transaction_event_logs")
    op.drop_index("ix_transaction_event_logs_session_id", table_name="transaction_event_logs")
    op.drop_table("transaction_event_logs")
