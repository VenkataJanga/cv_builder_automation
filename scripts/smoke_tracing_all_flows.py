from pathlib import Path
import json
import os

import pymysql
import requests

from src.core.env_loader import load_environment_variables
from src.core.constants import (
    JWT_EMAIL_CLAIM,
    JWT_FULL_NAME_CLAIM,
    JWT_LOCALE_CLAIM,
    JWT_ROLE_CLAIM,
    JWT_SUB_CLAIM,
    JWT_USER_ID_CLAIM,
)
from src.core.security.token_validator import create_access_token
from langsmith import Client


def get_user(username: str = "venkata.janga"):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, email, full_name, role FROM users WHERE username=%s",
            (username,),
        )
        user = cur.fetchone()
    conn.close()
    if not user:
        raise RuntimeError(f"User not found: {username}")
    return user


def auth_headers(user: dict) -> dict:
    token = create_access_token(
        {
            JWT_SUB_CLAIM: user["username"],
            JWT_USER_ID_CLAIM: user["id"],
            JWT_ROLE_CLAIM: user["role"],
            JWT_EMAIL_CLAIM: user["email"],
            JWT_FULL_NAME_CLAIM: user.get("full_name") or "",
            JWT_LOCALE_CLAIM: "en",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def run_flow_requests(base_url: str, headers: dict):
    # Conversation flow
    chat_resp = requests.post(
        f"{base_url}/chat",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"message": "start", "session_id": "default-session"}),
        timeout=30,
    )
    print("conversation_status", chat_resp.status_code)
    chat_resp.raise_for_status()
    session_id = chat_resp.json().get("session_id")
    if not session_id:
        raise RuntimeError("No session_id returned from /chat")

    # Recording flow
    correct_resp = requests.post(
        f"{base_url}/speech/correct",
        headers=headers,
        data={
            "transcript": "I am a senior Python developer with 8 years of experience in API and cloud development.",
            "session_id": session_id,
        },
        timeout=120,
    )
    print("recording_correct_status", correct_resp.status_code)

    # Audio upload flow
    storage_dir = Path("data/storage")
    audio_candidates = sorted(storage_dir.glob("*.webm"))
    if not audio_candidates:
        raise RuntimeError("No sample audio file found in data/storage")
    audio_path = audio_candidates[0]
    with audio_path.open("rb") as f:
        transcribe_resp = requests.post(
            f"{base_url}/speech/transcribe",
            headers=headers,
            files={"file": (audio_path.name, f, "audio/webm")},
            data={"session_id": session_id, "language": "en"},
            timeout=180,
        )
    print("audio_transcribe_status", transcribe_resp.status_code)

    # DOCX upload flow
    docx_path = Path("config/templates/ntt_data_hybrid_2026.docx")
    if not docx_path.exists():
        raise RuntimeError(f"DOCX sample file not found: {docx_path}")
    with docx_path.open("rb") as f:
        docx_resp = requests.post(
            f"{base_url}/cv/upload/document",
            headers=headers,
            files={"file": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"session_id": session_id},
            timeout=180,
        )
    print("docx_upload_status", docx_resp.status_code)

    return session_id


def fetch_recent_runs(limit: int = 30):
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    api_url = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    project_name = os.getenv("LANGCHAIN_PROJECT", "cv_builder_automation")

    session = requests.Session()
    verify_ssl = os.getenv("LANGSMITH_VERIFY_SSL", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    session.verify = verify_ssl

    client = Client(api_key=api_key, api_url=api_url, session=session)
    runs = list(client.list_runs(project_name=project_name, limit=limit))
    run_names = [getattr(r, "name", "") for r in runs]

    wanted_prefixes = ("conversation_", "speech_", "cv_")
    filtered = [name for name in run_names if any(name.startswith(p) for p in wanted_prefixes)]

    print("recent_total_runs", len(runs))
    print("recent_target_runs", len(filtered))
    for name in filtered[:20]:
        print("run_name", name)


def main():
    load_environment_variables()
    user = get_user()
    headers = auth_headers(user)
    base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")

    session_id = run_flow_requests(base_url, headers)
    print("session_id", session_id)
    fetch_recent_runs(limit=40)


if __name__ == "__main__":
    main()
