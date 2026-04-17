#!/usr/bin/env python3
"""Seed dummy RBAC data (roles/resources/permissions/users) into MySQL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.env_loader import load_environment_variables  # noqa: E402


def get_db_config() -> dict[str, str | int]:
    load_environment_variables()
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "cv_builder"),
    }


def seed_data() -> None:
    cfg = get_db_config()

    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cur:
            # Roles
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_roles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    role_name VARCHAR(64) NOT NULL UNIQUE,
                    description VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # Resources
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_resources (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    resource_name VARCHAR(64) NOT NULL UNIQUE,
                    description VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # Permissions per resource/action
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    permission_name VARCHAR(100) NOT NULL UNIQUE,
                    resource_id INT NOT NULL,
                    action_name VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_rbac_permissions_resource
                        FOREIGN KEY (resource_id) REFERENCES rbac_resources(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # Role-permission mapping
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_role_permissions (
                    role_id INT NOT NULL,
                    permission_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (role_id, permission_id),
                    CONSTRAINT fk_rbac_role_permissions_role
                        FOREIGN KEY (role_id) REFERENCES rbac_roles(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_rbac_role_permissions_permission
                        FOREIGN KEY (permission_id) REFERENCES rbac_permissions(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # Dummy users and role assignment
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    full_name VARCHAR(255) NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rbac_user_roles (
                    user_id INT NOT NULL,
                    role_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, role_id),
                    CONSTRAINT fk_rbac_user_roles_user
                        FOREIGN KEY (user_id) REFERENCES rbac_users(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_rbac_user_roles_role
                        FOREIGN KEY (role_id) REFERENCES rbac_roles(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            roles = [
                ("admin", "Full access"),
                ("reviewer", "Can review CVs"),
                ("user", "Regular user"),
                ("delivery_manager", "Delivery owner"),
                ("cv_editor", "Can edit CV content"),
            ]
            cur.executemany(
                """
                INSERT INTO rbac_roles(role_name, description)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE description = VALUES(description)
                """,
                roles,
            )

            resources = [
                ("cv", "CV creation and editing"),
                ("review", "Review workflow"),
                ("export", "Export endpoints"),
                ("templates", "Template management"),
                ("session", "Session data"),
            ]
            cur.executemany(
                """
                INSERT INTO rbac_resources(resource_name, description)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE description = VALUES(description)
                """,
                resources,
            )

            # Build permission rows by joining resource ids
            permission_spec = [
                ("create_cv", "cv", "create"),
                ("edit_cv", "cv", "edit"),
                ("review_cv", "review", "review"),
                ("approve_cv", "review", "approve"),
                ("export_cv", "export", "export"),
                ("manage_templates", "templates", "manage"),
                ("read_session", "session", "read"),
            ]

            for perm_name, resource_name, action_name in permission_spec:
                cur.execute(
                    """
                    INSERT INTO rbac_permissions(permission_name, resource_id, action_name)
                    SELECT %s, r.id, %s
                    FROM rbac_resources r
                    WHERE r.resource_name = %s
                    ON DUPLICATE KEY UPDATE
                        action_name = VALUES(action_name),
                        resource_id = VALUES(resource_id)
                    """,
                    (perm_name, action_name, resource_name),
                )

            role_permissions = {
                "admin": [
                    "create_cv", "edit_cv", "review_cv", "approve_cv",
                    "export_cv", "manage_templates", "read_session",
                ],
                "delivery_manager": [
                    "create_cv", "edit_cv", "review_cv", "approve_cv",
                    "export_cv", "read_session",
                ],
                "reviewer": ["review_cv", "export_cv", "read_session"],
                "cv_editor": ["create_cv", "edit_cv", "export_cv", "read_session"],
                "user": ["create_cv", "edit_cv", "export_cv", "read_session"],
            }

            for role_name, perms in role_permissions.items():
                for perm_name in perms:
                    cur.execute(
                        """
                        INSERT IGNORE INTO rbac_role_permissions(role_id, permission_id)
                        SELECT rr.id, rp.id
                        FROM rbac_roles rr
                        JOIN rbac_permissions rp ON rp.permission_name = %s
                        WHERE rr.role_name = %s
                        """,
                        (perm_name, role_name),
                    )

            users = [
                ("admin_nttdata", "admin_nttdata@nttdata.com", "Admin Demo", "admin"),
                ("reviewer_nttdata", "reviewer_nttdata@nttdata.com", "Reviewer Demo", "reviewer"),
                ("editor_nttdata", "editor_nttdata@nttdata.com", "Editor Demo", "cv_editor"),
                ("manager_nttdata", "manager_nttdata@nttdata.com", "Delivery Manager Demo", "delivery_manager"),
                ("user_nttdata", "user_nttdata@nttdata.com", "User Demo", "user"),
            ]

            for username, email, full_name, role_name in users:
                cur.execute(
                    """
                    INSERT INTO rbac_users(username, email, full_name)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE full_name = VALUES(full_name)
                    """,
                    (username, email, full_name),
                )

                cur.execute(
                    """
                    INSERT IGNORE INTO rbac_user_roles(user_id, role_id)
                    SELECT u.id, r.id
                    FROM rbac_users u
                    JOIN rbac_roles r ON r.role_name = %s
                    WHERE u.username = %s
                    """,
                    (role_name, username),
                )

        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM rbac_roles")
            roles_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM rbac_resources")
            resources_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM rbac_permissions")
            perms_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM rbac_users")
            users_count = cur.fetchone()["c"]

        print("RBAC dummy data seeded successfully")
        print(f"roles={roles_count}, resources={resources_count}, permissions={perms_count}, users={users_count}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_data()
