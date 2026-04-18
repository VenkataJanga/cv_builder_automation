#!/usr/bin/env python3
"""Seed hashed auth users into the main users table for OAuth2 testing."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.env_loader import load_environment_variables  # noqa: E402
from src.core.security.password_hashing import hash_password  # noqa: E402


def db_config() -> dict[str, str | int]:
    load_environment_variables()
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "cv_builder"),
    }


def seed_users() -> None:
    cfg = db_config()
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

    # Require explicit configuration to avoid shipping known default credentials.
    plain_password = os.getenv("SEED_AUTH_PASSWORD", "").strip()
    if not plain_password:
        raise RuntimeError(
            "SEED_AUTH_PASSWORD is required. Example: $env:SEED_AUTH_PASSWORD='replace-with-strong-password'"
        )
    hashed = hash_password(plain_password)

    users = [
        ("venkata.janga", "venkata.janga@cvbuilder.local", "Venkata Janga", hashed, "admin"),
        ("aarthy.s", "aarthy.s@cvbuilder.local", "Aarthy S", hashed, "reviewer"),
        ("madhan.k", "madhan.k@cvbuilder.local", "Madhan K", hashed, "cv_editor"),
        ("priya.r", "priya.r@cvbuilder.local", "Priya R", hashed, "delivery_manager"),
        ("kiran.p", "kiran.p@cvbuilder.local", "Kiran P", hashed, "user"),
    ]

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    full_name VARCHAR(255) NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.executemany(
                """
                INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
                VALUES (%s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    email = VALUES(email),
                    full_name = VALUES(full_name),
                    hashed_password = VALUES(hashed_password),
                    role = VALUES(role),
                    is_active = 1
                """,
                users,
            )

        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users")
            total = cur.fetchone()["c"]
            cur.execute(
                "SELECT username, role, is_active FROM users ORDER BY id"
            )
            rows = cur.fetchall()

        print("Auth users seeded successfully.")
        print(f"total_users={total}")
        print("seed_password=<configured via SEED_AUTH_PASSWORD>")
        for row in rows:
            print(f"{row['username']} | {row['role']} | active={row['is_active']}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_users()
