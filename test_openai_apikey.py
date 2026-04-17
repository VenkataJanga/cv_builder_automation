"""
Quick smoke-test: verify the OPENAI_API_KEY in .env is valid and can reach
the OpenAI API.  Run with:

    python -m pytest test_openai_apikey.py -v
"""

import os
import pytest
from dotenv import load_dotenv

# Load .env from the repo root so the key is available without any server setup.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)


def _api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        pytest.skip("OPENAI_API_KEY is not set in .env — skipping API key check.")
    return key


def test_openai_api_key_is_present():
    """The key must exist and look like a real OpenAI key (starts with 'sk-')."""
    key = _api_key()
    assert key.startswith("sk-"), (
        f"OPENAI_API_KEY does not look like a valid OpenAI key "
        f"(expected prefix 'sk-', got '{key[:8]}...')"
    )


def test_openai_api_key_is_accepted_by_openai():
    """Make a minimal API call (models list) to confirm the key is active."""
    try:
        import httpx
        import openai
    except ImportError:
        pytest.skip("openai / httpx package not installed.")

    # Honour OPENAI_VERIFY_SSL=false (corporate proxies with SSL inspection).
    verify_ssl = os.getenv("OPENAI_VERIFY_SSL", "true").lower() not in ("false", "0", "no")
    http_client = httpx.Client(verify=verify_ssl)

    client = openai.OpenAI(api_key=_api_key(), http_client=http_client)

    try:
        models = client.models.list()
    except openai.AuthenticationError as exc:
        pytest.fail(
            f"OPENAI_API_KEY was REJECTED by OpenAI (401 Authentication Error).\n"
            f"Details: {exc}"
        )
    except openai.APIConnectionError as exc:
        pytest.fail(
            f"Could not reach the OpenAI API — check your network / proxy / SSL cert.\n"
            f"Tip: set OPENAI_VERIFY_SSL=false in .env if behind a corporate proxy.\n"
            f"Details: {exc}"
        )

    model_ids = [m.id for m in models.data]
    assert len(model_ids) > 0, "API returned an empty model list — unexpected."
    print(f"\n  Key OK — {len(model_ids)} models accessible (e.g. {model_ids[0]})")
