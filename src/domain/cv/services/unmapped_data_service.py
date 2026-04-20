from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any, Dict
from uuid import uuid4


class UnmappedDataService:
    """Helpers to preserve source details that cannot be mapped to canonical fields."""

    ATTRIBUTES_KEY = "attributes"

    def ensure_sections(self, canonical_cv: Dict[str, Any]) -> Dict[str, Any]:
        canonical_cv.setdefault("unmappedData", {})
        canonical_cv["unmappedData"].setdefault(self.ATTRIBUTES_KEY, [])
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
            self._record_structured_unmapped(canonical_cv, source, key, value)
            return

        if isinstance(existing, list):
            if isinstance(value, list):
                existing.extend(deepcopy(value))
            else:
                existing.append(deepcopy(value))
            self._record_structured_unmapped(canonical_cv, source, key, value)
            return

        if isinstance(existing, dict) and isinstance(value, dict):
            merged = deepcopy(existing)
            merged.update(deepcopy(value))
            source_bucket[key] = merged
            self._record_structured_unmapped(canonical_cv, source, key, value)
            return

        source_bucket[key] = deepcopy(value)
        self._record_structured_unmapped(canonical_cv, source, key, value)

    def preserve_unmapped_attribute(
        self,
        canonical_cv: Dict[str, Any],
        source: str,
        original_label: str,
        extracted_value: Any,
        source_section: str = "",
        source_path: str = "",
        confidence: float | None = None,
        mapping_status: str = "unmapped",
        normalized_label: str | None = None,
    ) -> None:
        """Write one structured Others attribute record into unmappedData.attributes."""
        if not self._is_truthy(extracted_value):
            return

        self.ensure_sections(canonical_cv)
        attributes = canonical_cv["unmappedData"].setdefault(self.ATTRIBUTES_KEY, [])
        label = str(original_label or "").strip() or "unknown"
        path = str(source_path or "").strip() or label
        norm = normalized_label or self._normalize_label(label)

        existing = self._find_existing_attribute(attributes, source, path, extracted_value)
        now_iso = datetime.now(timezone.utc).isoformat()
        if existing is not None:
            existing["occurrenceCount"] = int(existing.get("occurrenceCount", 1) or 1) + 1
            existing["lastSeenAt"] = now_iso
            return

        record = {
            "attributeId": str(uuid4()),
            "originalLabel": label,
            "normalizedLabel": norm,
            "extractedValue": deepcopy(extracted_value),
            "valueType": self._value_type(extracted_value),
            "source": str(source or "unknown"),
            "sourceSection": str(source_section or ""),
            "sourcePath": path,
            "confidence": confidence,
            "mappingStatus": str(mapping_status or "unmapped"),
            "firstSeenAt": now_iso,
            "lastSeenAt": now_iso,
            "occurrenceCount": 1,
            "promotionCandidate": False,
            "reviewStatus": "pending",
        }
        attributes.append(record)

    def normalize_legacy_unmapped_data(self, canonical_cv: Dict[str, Any]) -> int:
        """Backfill structured unmappedData.attributes from legacy source buckets."""
        self.ensure_sections(canonical_cv)
        unmapped = canonical_cv.get("unmappedData") or {}
        migrated = 0

        for source, payload in list(unmapped.items()):
            if source == self.ATTRIBUTES_KEY:
                continue
            if not self._is_truthy(payload):
                continue
            before = len(unmapped.get(self.ATTRIBUTES_KEY, []))
            self._record_structured_unmapped(canonical_cv, source, "legacy", payload)
            after = len(unmapped.get(self.ATTRIBUTES_KEY, []))
            migrated += max(0, after - before)

        return migrated

    def get_unmapped_frequency(self, canonical_cv: Dict[str, Any]) -> Dict[str, int]:
        """Return normalized-label occurrence counts for promotion review."""
        self.ensure_sections(canonical_cv)
        freq: Dict[str, int] = {}
        for item in canonical_cv.get("unmappedData", {}).get(self.ATTRIBUTES_KEY, []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("normalizedLabel") or item.get("originalLabel") or "unknown").strip().lower()
            if not label:
                continue
            freq[label] = freq.get(label, 0) + int(item.get("occurrenceCount", 1) or 1)
        return freq

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

    def _record_structured_unmapped(
        self,
        canonical_cv: Dict[str, Any],
        source: str,
        key: str,
        value: Any,
    ) -> None:
        for flattened in self._flatten_unmapped(str(key or "unknown"), value):
            self.preserve_unmapped_attribute(
                canonical_cv=canonical_cv,
                source=source,
                original_label=flattened["leaf_label"],
                extracted_value=flattened["value"],
                source_section=str(key or ""),
                source_path=flattened["path"],
                mapping_status="unmapped",
            )

    def _flatten_unmapped(self, root_label: str, value: Any) -> list[Dict[str, Any]]:
        rows: list[Dict[str, Any]] = []

        def walk(path: str, node: Any) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    k_str = str(k)
                    next_path = f"{path}.{k_str}" if path else k_str
                    walk(next_path, v)
                return
            if isinstance(node, list):
                for idx, item in enumerate(node):
                    next_path = f"{path}[{idx}]"
                    walk(next_path, item)
                return
            if not self._is_truthy(node):
                return

            leaf = path.split(".")[-1] if path else root_label
            leaf = leaf.split("[")[0]
            rows.append(
                {
                    "path": path or root_label,
                    "leaf_label": leaf or root_label,
                    "value": deepcopy(node),
                }
            )

        walk(root_label, value)
        return rows

    @staticmethod
    def _normalize_label(label: str) -> str:
        collapsed = " ".join(str(label or "").strip().split())
        return collapsed.lower()

    @staticmethod
    def _value_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def _find_existing_attribute(
        self,
        attributes: list[Any],
        source: str,
        source_path: str,
        extracted_value: Any,
    ) -> Dict[str, Any] | None:
        for item in attributes:
            if not isinstance(item, dict):
                continue
            if str(item.get("source") or "") != str(source or ""):
                continue
            if str(item.get("sourcePath") or "") != str(source_path or ""):
                continue
            existing_val = item.get("extractedValue")
            if self._stable_json(existing_val) == self._stable_json(extracted_value):
                return item
        return None

    @staticmethod
    def _stable_json(value: Any) -> str:
        try:
            return json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
        except Exception:
            return str(value)
