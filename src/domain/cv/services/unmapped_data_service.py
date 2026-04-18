from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict


class UnmappedDataService:
    """Helpers to preserve source details that cannot be mapped to canonical fields."""

    def ensure_sections(self, canonical_cv: Dict[str, Any]) -> Dict[str, Any]:
        canonical_cv.setdefault("unmappedData", {})
        canonical_cv.setdefault("sourceSnapshots", {})
        canonical_cv.setdefault("mappingWarnings", [])
        return canonical_cv

    def preserve_unmapped(
        self,
        canonical_cv: Dict[str, Any],
        source: str,
        key: str,
        value: Any,
    ) -> None:
        if not self._is_truthy(value):
            return
        self.ensure_sections(canonical_cv)
        source_bucket = canonical_cv["unmappedData"].setdefault(source, {})

        existing = source_bucket.get(key)
        if existing is None:
            source_bucket[key] = deepcopy(value)
            return

        if isinstance(existing, list):
            if isinstance(value, list):
                existing.extend(deepcopy(value))
            else:
                existing.append(deepcopy(value))
            return

        if isinstance(existing, dict) and isinstance(value, dict):
            merged = deepcopy(existing)
            merged.update(deepcopy(value))
            source_bucket[key] = merged
            return

        source_bucket[key] = deepcopy(value)

    def preserve_snapshot(
        self,
        canonical_cv: Dict[str, Any],
        source: str,
        entry: Dict[str, Any],
    ) -> None:
        if not self._is_truthy(entry):
            return
        self.ensure_sections(canonical_cv)
        source_bucket = canonical_cv["sourceSnapshots"].setdefault(source, {})
        entries = source_bucket.setdefault("entries", [])
        payload = deepcopy(entry)
        payload.setdefault("capturedAt", datetime.now(timezone.utc).isoformat())
        entries.append(payload)

    def add_mapping_warning(
        self,
        canonical_cv: Dict[str, Any],
        source: str,
        warning: str,
        context: Dict[str, Any] | None = None,
    ) -> None:
        if not self._is_truthy(warning):
            return
        self.ensure_sections(canonical_cv)
        canonical_cv["mappingWarnings"].append(
            {
                "source": source,
                "warning": str(warning),
                "context": deepcopy(context or {}),
                "capturedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

    @staticmethod
    def collect_unmapped_top_level(
        payload: Dict[str, Any],
        known_keys: set[str],
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        return {k: deepcopy(v) for k, v in payload.items() if k not in known_keys and UnmappedDataService._is_truthy(v)}

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return bool(value)
