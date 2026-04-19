from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.core.i18n.locale_resolver import get_default_locale, normalize_locale


def _messages_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "locales" / "messages"


@lru_cache(maxsize=16)
def _load_catalog(locale: str) -> dict[str, Any]:
    catalog_path = _messages_dir() / f"{locale}.yaml"
    if not catalog_path.exists():
        return {}

    with catalog_path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    return payload if isinstance(payload, dict) else {}


def _get_nested(payload: dict[str, Any], key: str) -> str | None:
    node: Any = payload
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]

    if isinstance(node, str):
        return node
    return None


def t(key: str, locale: str | None = None, **params: Any) -> str:
    resolved_locale = normalize_locale(locale) or get_default_locale()
    catalog = _load_catalog(resolved_locale)
    default_catalog = _load_catalog(get_default_locale())

    template = _get_nested(catalog, key) or _get_nested(default_catalog, key) or key
    try:
        return template.format(**params)
    except Exception:
        return template
