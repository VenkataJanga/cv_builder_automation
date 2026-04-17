"""Initial schema for auth, RBAC, and session persistence

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260416_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_rbac_roles_name", "rbac_roles", ["role_name"], unique=True)

    op.create_table(
        "rbac_resources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("resource_name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_rbac_resources_name", "rbac_resources", ["resource_name"], unique=True)

    op.create_table(
        "rbac_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("permission_name", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("action_name", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["resource_id"], ["rbac_resources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rbac_permissions_name", "rbac_permissions", ["permission_name"], unique=True)

    op.create_table(
        "rbac_role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["rbac_permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "cv_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("canonical_cv", sa.Text(), nullable=False),
        sa.Column("validation_results", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.Column("exported_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("source_history", sa.Text(), nullable=False),
        sa.Column("uploaded_artifacts", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=False),
        sa.Column("workflow_state", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_cv_sessions_expires_at", "cv_sessions", ["expires_at"], unique=False)
    op.create_index("ix_cv_sessions_status", "cv_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cv_sessions_status", table_name="cv_sessions")
    op.drop_index("ix_cv_sessions_expires_at", table_name="cv_sessions")
    op.drop_table("cv_sessions")

    op.drop_table("rbac_role_permissions")

    op.drop_index("ix_rbac_permissions_name", table_name="rbac_permissions")
    op.drop_table("rbac_permissions")

    op.drop_index("ix_rbac_resources_name", table_name="rbac_resources")
    op.drop_table("rbac_resources")

    op.drop_index("ix_rbac_roles_name", table_name="rbac_roles")
    op.drop_table("rbac_roles")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
