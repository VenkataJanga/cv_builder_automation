#!/usr/bin/env python3
"""Quick verification for RBAC seed data."""

import os
import sys
from pathlib import Path

import pymysql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.env_loader import load_environment_variables  # noqa: E402


def main() -> None:
    load_environment_variables()

    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "cv_builder"),
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rr.role_name, rsrc.resource_name, rp.permission_name
                FROM rbac_role_permissions rrp
                JOIN rbac_roles rr ON rr.id = rrp.role_id
                JOIN rbac_permissions rp ON rp.id = rrp.permission_id
                JOIN rbac_resources rsrc ON rsrc.id = rp.resource_id
                ORDER BY rr.role_name, rsrc.resource_name, rp.permission_name
                """
            )
            rows = cur.fetchall()

        print(f"total_mappings={len(rows)}")
        for row in rows:
            print(f"{row['role_name']} | {row['resource_name']} | {row['permission_name']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
