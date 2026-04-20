from pathlib import Path
import json
import os
from datetime import datetime, timezone

import pymysql
import requests
from langsmith import Client

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


def get_user(username: str = "venkata.janga") -> dict:
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


def call_flows(base_url: str, headers: dict) -> tuple[str, dict]:
    status_map = {}
    run_recording = os.getenv("RUN_RECORDING_FLOW", "true").lower() == "true"
    run_audio = os.getenv("RUN_AUDIO_FLOW", "true").lower() == "true"
    run_docx = os.getenv("RUN_DOCX_FLOW", "true").lower() == "true"

    print("calling /chat start", flush=True)
    chat_start = requests.post(
        f"{base_url}/chat",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"message": "start", "session_id": "default-session"}),
        timeout=30,
    )
    status_map["conversation_start"] = chat_start.status_code
    print("conversation_start", chat_start.status_code, flush=True)
    chat_start.raise_for_status()
    session_id = chat_start.json().get("session_id")
    if not session_id:
        raise RuntimeError("No session_id returned from /chat")

    print("calling /chat answer", flush=True)
    chat_answer = requests.post(
        f"{base_url}/chat",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"message": "Python developer", "session_id": session_id}),
        timeout=30,
    )
    status_map["conversation_answer"] = chat_answer.status_code
    print("conversation_answer", chat_answer.status_code, flush=True)

    if run_recording:
        try:
            print("calling /speech/correct", flush=True)
            record_correct = requests.post(
                f"{base_url}/speech/correct",
                headers=headers,
                data={
                    "transcript": "I am a Python developer with cloud and API experience.",
                    "session_id": session_id,
                },
                timeout=45,
            )
            status_map["recording_correct"] = record_correct.status_code
            print("recording_correct", record_correct.status_code, flush=True)
        except Exception as exc:
            status_map["recording_correct"] = f"error:{exc}"
            print("recording_correct error", exc, flush=True)
    else:
        status_map["recording_correct"] = "skipped"

    audio_candidates = sorted(Path("data/storage").glob("*.webm"))
    if run_audio and audio_candidates:
        try:
            print("calling /speech/transcribe", audio_candidates[0].name, flush=True)
            with audio_candidates[0].open("rb") as f:
                audio_upload = requests.post(
                    f"{base_url}/speech/transcribe",
                    headers=headers,
                    files={"file": (audio_candidates[0].name, f, "audio/webm")},
                    data={"session_id": session_id, "language": "en"},
                    timeout=60,
                )
            status_map["audio_upload"] = audio_upload.status_code
            print("audio_upload", audio_upload.status_code, flush=True)
        except Exception as exc:
            status_map["audio_upload"] = f"error:{exc}"
            print("audio_upload error", exc, flush=True)
    elif run_audio:
        status_map["audio_upload"] = "skipped-no-audio"
    else:
        status_map["audio_upload"] = "skipped"

    docx_path = Path("config/templates/ntt_data_hybrid_2026.docx")
    if run_docx and docx_path.exists():
        try:
            print("calling /cv/upload/document", docx_path.name, flush=True)
            with docx_path.open("rb") as f:
                docx_upload = requests.post(
                    f"{base_url}/cv/upload/document",
                    headers=headers,
                    files={"file": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                    data={"session_id": session_id},
                    timeout=60,
                )
            status_map["docx_upload"] = docx_upload.status_code
            print("docx_upload", docx_upload.status_code, flush=True)
        except Exception as exc:
            status_map["docx_upload"] = f"error:{exc}"
            print("docx_upload error", exc, flush=True)
    elif run_docx:
        status_map["docx_upload"] = "skipped-no-docx"
    else:
        status_map["docx_upload"] = "skipped"

    return session_id, status_map


def fetch_recent_flow_runs() -> list[tuple[str, str, str]]:
    session = requests.Session()
    session.verify = False
    client = Client(
        api_key=os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"),
        api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        session=session,
    )

    project = os.getenv("LANGCHAIN_PROJECT", "cv_builder_automation")
    runs = list(client.list_runs(project_name=project, limit=20))
    now = datetime.now(timezone.utc)
    wanted = {
        "conversation_chat_submit_answer",
        "speech_audio_upload_transcribe",
        "speech_start_recording_correct_transcript",
        "cv_upload_cv_document",
    }

    out = []
    for run in runs:
        if run.name not in wanted:
            continue
        age_seconds = (now - run.start_time).total_seconds()
        if age_seconds < 1800:
            out.append((str(run.id), run.name, run.start_time.isoformat()))
    return out


def main() -> None:
    load_environment_variables()
    user = get_user()
    headers = auth_headers(user)
    base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")

    session_id, statuses = call_flows(base_url, headers)
    recent = fetch_recent_flow_runs()

    print("session_id", session_id)
    print("statuses", statuses)
    print("recent_flow_runs", len(recent))
    for run_id, run_name, start_time in recent:
        print("run", run_id, run_name, start_time)


if __name__ == "__main__":
    main()
