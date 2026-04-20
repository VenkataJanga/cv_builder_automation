from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class FieldCheckResult:
    field_path: str
    value: str
    supported: bool
    evidence: str


class QualityMetricsService:
    """
    Computes practical quality metrics and field-level traceability.

    Metrics are heuristics aligned for production monitoring of extraction reliability:
    - precision: supported extracted fields / extracted fields
    - recall: supported extracted fields / expected fields
    - accuracy: same operational definition as mapping accuracy in this pipeline
    - hallucination_rate: unsupported extracted fields / extracted fields
    - completeness_score: extracted fields / expected fields
    """

    _IGNORE_KEYS = {
        "id",
        "cvid",
        "session_id",
        "schema_version",
        "created_at",
        "updated_at",
    }

    def evaluate(self, canonical_cv: Dict[str, Any], validation_result: Dict[str, Any] | None = None) -> Dict[str, Any]:
        canonical = canonical_cv or {}
        source_snapshots = canonical.get("sourceSnapshots", {}) or {}

        expected_fields = self._collect_expected_field_paths(canonical)
        extracted = self._collect_extracted_field_values(canonical)
        corpus = self._build_evidence_corpus(source_snapshots)

        checks: List[FieldCheckResult] = []
        supported_count = 0

        for field_path, value in extracted:
            supported, evidence = self._is_supported(value, corpus)
            if supported:
                supported_count += 1
            checks.append(
                FieldCheckResult(
                    field_path=field_path,
                    value=value,
                    supported=supported,
                    evidence=evidence,
                )
            )

        extracted_count = len(extracted)
        expected_count = max(1, len(expected_fields))
        unsupported_count = extracted_count - supported_count

        precision = supported_count / extracted_count if extracted_count else 1.0
        recall = supported_count / expected_count
        mapping_accuracy = precision
        hallucination_rate = unsupported_count / extracted_count if extracted_count else 0.0
        completeness_score = extracted_count / expected_count

        validation = validation_result or {}
        validation_pass = bool(validation.get("can_export") or validation.get("can_save") or validation.get("success"))

        return {
            "definitions": {
                "precision": "supported_extracted_fields / extracted_fields",
                "recall": "supported_extracted_fields / expected_fields",
                "accuracy": "mapping_accuracy operationally equivalent to precision for current mapper",
                "hallucination_rate": "unsupported_extracted_fields / extracted_fields",
                "completeness_score": "extracted_fields / expected_fields",
                "validation_pass_rate": "1 if deterministic validation passes else 0",
            },
            "counts": {
                "expected_fields": expected_count,
                "extracted_fields": extracted_count,
                "supported_fields": supported_count,
                "unsupported_fields": unsupported_count,
            },
            "metrics": {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "accuracy": round(mapping_accuracy, 4),
                "hallucination_rate": round(hallucination_rate, 4),
                "completeness_score": round(completeness_score, 4),
                "validation_pass_rate": 1.0 if validation_pass else 0.0,
            },
            "field_traceability": [
                {
                    "field_path": item.field_path,
                    "value": item.value,
                    "support_status": "supported" if item.supported else "unsupported",
                    "evidence": item.evidence,
                }
                for item in checks
            ],
        }

    def _collect_expected_field_paths(self, canonical: Dict[str, Any]) -> List[str]:
        expected: List[str] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    key_norm = str(key).strip().lower()
                    if key_norm in self._IGNORE_KEYS:
                        continue
                    next_path = f"{path}.{key}" if path else str(key)
                    walk(value, next_path)
                return
            if isinstance(node, list):
                if path:
                    expected.append(path)
                return
            if path:
                expected.append(path)

        walk(canonical.get("candidate", {}), "candidate")
        walk(canonical.get("skills", {}), "skills")
        walk(canonical.get("experience", {}), "experience")
        walk(canonical.get("education", []), "education")
        walk(canonical.get("certifications", []), "certifications")
        walk(canonical.get("unmappedData", {}), "unmappedData")
        return list({item for item in expected if item})

    def _collect_extracted_field_values(self, canonical: Dict[str, Any]) -> List[Tuple[str, str]]:
        extracted: List[Tuple[str, str]] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    key_norm = str(key).strip().lower()
                    if key_norm in self._IGNORE_KEYS:
                        continue
                    next_path = f"{path}.{key}" if path else str(key)
                    walk(value, next_path)
                return

            if isinstance(node, list):
                for idx, item in enumerate(node):
                    if isinstance(item, (dict, list)):
                        walk(item, f"{path}[{idx}]")
                    else:
                        text = self._normalize_text(item)
                        if text:
                            extracted.append((path, text))
                return

            text = self._normalize_text(node)
            if text:
                extracted.append((path, text))

        walk(canonical.get("candidate", {}), "candidate")
        walk(canonical.get("skills", {}), "skills")
        walk(canonical.get("experience", {}), "experience")
        walk(canonical.get("education", []), "education")
        walk(canonical.get("certifications", []), "certifications")
        walk(canonical.get("unmappedData", {}), "unmappedData")
        return extracted

    def _build_evidence_corpus(self, source_snapshots: Dict[str, Any]) -> List[str]:
        corpus: List[str] = []

        def add_text(value: Any) -> None:
            if isinstance(value, str):
                normalized = self._normalize_text(value)
                if normalized:
                    corpus.append(normalized)
                return
            if isinstance(value, (int, float)):
                corpus.append(str(value))
                return
            if isinstance(value, list):
                for item in value:
                    add_text(item)
                return
            if isinstance(value, dict):
                for item in value.values():
                    add_text(item)

        add_text(source_snapshots)
        return corpus

    def _is_supported(self, value: str, corpus: List[str]) -> Tuple[bool, str]:
        target = self._normalize_text(value)
        if not target:
            return True, ""

        # Very small tokens/numbers are fragile; skip strict unsupported penalties.
        if len(target) <= 2:
            return True, ""

        for evidence in corpus:
            if target in evidence:
                return True, evidence[:220]

        # Year-like evidence fallback.
        if re.fullmatch(r"(19|20)\d{2}", target):
            for evidence in corpus:
                if target in evidence:
                    return True, evidence[:220]

        return False, ""

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        lowered = text.lower().strip(" ,.;:-")
        if lowered in {"none", "null", "n/a", "na", "undefined", "[]", "{}"}:
            return ""
        text = re.sub(r"\s+", " ", text)
        return text.lower()
