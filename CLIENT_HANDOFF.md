# Client Handoff Checklist

## 1) Release Package Hygiene

- Confirm no real secrets are committed.
- Confirm `.env` is not included in source control or release bundle.
- Confirm generated files are not shipped:
  - `log/*.json`
  - `data/storage/uploads/`
  - `data/storage/sessions/`
- Confirm only template/sample env files are shipped:
  - `.env.example`
  - `deployments/local/env.example`

## 2) Prerequisites

- Python 3.11+ (project currently validated on Python 3.13 runtime image)
- MySQL 8.x
- Network access to OpenAI APIs if AI features are enabled

## 3) Environment Configuration

Create a runtime env file from example and set all required values.

Environment file resolution behavior:

- If `ENV` is set (for example `ENV=dev`), the app loads `.env.dev` first and falls back to `.env`.
- If `ENV` is not set (or `ENV=local`), the app loads `.env`.
- Recommended naming: `.env.dev`, `.env.uat`, `.env.prod` (do not commit real secrets).

Required minimum values:

- `OPENAI_API_KEY`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `SECRET_KEY`
- `SESSION_REPOSITORY_BACKEND` (use `mysql` for DB-backed sessions)

Optional but recommended:

- `OPENAI_VERIFY_SSL=true`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `TOKEN_EXPIRE_MINUTES`
- `SEED_DEMO_PASSWORD` (required only when running seed script)

## 4) Database and Migration Runbook

### Fresh database

1. Install project dependencies.
2. Apply schema migrations.
3. Seed demo auth users (optional, local/demo only).

PowerShell sequence:

```powershell
$env:PYTHONPATH='.'
$env:SEED_DEMO_PASSWORD='replace-with-strong-demo-password'
python -m alembic -c alembic.ini upgrade head
python scripts/seed_auth_users.py
```

### Existing database already containing tables

If migration fails because tables already exist, align Alembic state first:

```powershell
$env:PYTHONPATH='.'
python -m alembic -c alembic.ini stamp head
```

Then continue normal migration workflow for subsequent revisions.

## 5) Local Startup

```powershell
pip install -e .
$env:PYTHONPATH='.'
$env:SESSION_REPOSITORY_BACKEND='mysql'
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Expected endpoints:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 6) Smoke Test Checklist

- `GET /health` returns 200.
- `GET /openapi.json` returns 200.
- Protected route returns 401/403 without token.
- `POST /auth/token` returns access token for valid user.
- Protected route returns 200 with Bearer token.
- Session create and retrieval flow works end-to-end.
- Preview endpoint works for seeded/test session.
- Export DOCX returns 200 for export-eligible payload.
- Export PDF returns 200 for export-eligible payload.

## 7) Security Checklist

- Rotate all secrets before client production deployment.
- Use a strong `SECRET_KEY` (32+ random chars minimum).
- Do not use demo users in production.
- Restrict CORS origins to client-approved domains.
- Ensure TLS is terminated correctly in target environment.
- Keep `.env` and runtime secrets outside source control.

## 8) Deployment Notes

### Local Docker

- Use `deployments/local/docker-compose.yml` with `deployments/local/env.example` as template.
- `DB_PASSWORD` and `DB_ROOT_PASSWORD` are required and must be explicitly set.

### AKS/ACA

- Ensure secret objects are populated before deployment.
- Verify all referenced secret keys exist in target namespace/environment.

## 9) Validation Before Sign-Off

- Run test suite.
- Run migration command against target DB.
- Execute smoke tests listed above.
- Verify no secrets or generated artifacts are included in final package.

## 10) Handoff Artifacts to Share

- Source code package (without `.env` or generated logs/uploads)
- `README.md`
- `CLIENT_HANDOFF.md`
- `.env.example`
- `deployments/local/env.example`
- `alembic.ini` and `migrations/`
- Deployment manifests under `deployments/`
