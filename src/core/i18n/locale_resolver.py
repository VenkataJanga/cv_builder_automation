from __future__ import annotations

from src.core.config.settings import settings


def _parse_supported_locales() -> list[str]:
    raw = settings.SUPPORTED_LOCALES or ""
    parsed = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return parsed or ["en"]


def normalize_locale(locale: str | None) -> str | None:
    if not locale:
        return None
    candidate = locale.strip().replace("_", "-").lower()
    if not candidate:
        return None

    supported = _parse_supported_locales()
    if candidate in supported:
        return candidate

    base = candidate.split("-", 1)[0]
    if base in supported:
        return base

    return None


def get_default_locale() -> str:
    return normalize_locale(settings.DEFAULT_LOCALE) or "en"


def get_supported_locales() -> list[str]:
    return _parse_supported_locales()


def resolve_locale(
    explicit_locale: str | None = None,
    session_ui_locale: str | None = None,
    user_preferred_locale: str | None = None,
) -> str:
    for candidate in (explicit_locale, session_ui_locale, user_preferred_locale):
        normalized = normalize_locale(candidate)
        if normalized:
            return normalized
    return get_default_locale()
