"""Add actor and event_message fields to transaction_event_logs

Revision ID: 20260418_0003
Revises: 20260418_0002
Create Date: 2026-04-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260418_0003"
down_revision: Union[str, Sequence[str], None] = "20260418_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transaction_event_logs", sa.Column("actor_user_id", sa.BigInteger(), nullable=True))
    op.add_column("transaction_event_logs", sa.Column("actor_username", sa.String(length=128), nullable=True))
    op.add_column("transaction_event_logs", sa.Column("event_message", sa.Text(), nullable=True))

    op.create_index(
        "ix_transaction_event_logs_actor_user_id",
        "transaction_event_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_event_logs_actor_username",
        "transaction_event_logs",
        ["actor_username"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_event_logs_actor_username", table_name="transaction_event_logs")
    op.drop_index("ix_transaction_event_logs_actor_user_id", table_name="transaction_event_logs")

    op.drop_column("transaction_event_logs", "event_message")
    op.drop_column("transaction_event_logs", "actor_username")
    op.drop_column("transaction_event_logs", "actor_user_id")
