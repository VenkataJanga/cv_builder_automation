import re
from typing import Dict, Any, List


class ResumeParser:
    def parse(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "personal_details": {},
            "summary": {},
            "skills": {},
            "work_experience": [],
        }

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return result

        if self._looks_like_name(lines[0]):
            result["personal_details"]["full_name"] = lines[0]

        summary = self._extract_section_block(text, ["summary", "profile", "about"])
        if summary:
            result["summary"]["professional_summary"] = summary

        primary = self._extract_inline_value(text, ["skills", "technical skills", "primary skills", "technologies"])
        if primary:
            result["skills"]["primary_skills"] = [s.strip() for s in re.split(r",|\||;", primary) if s.strip()]

        return result

    def low_confidence(self, parsed: Dict[str, Any]) -> bool:
        personal = parsed.get("personal_details", {})
        skills = parsed.get("skills", {})
        return not personal.get("full_name") or not skills.get("primary_skills")

    def _extract_inline_value(self, text: str, keywords: List[str]) -> str:
        pattern = r"(?im)^\s*(" + "|".join([re.escape(k) for k in keywords]) + r")\s*[:\-]\s*(.+)$"
        match = re.search(pattern, text)
        if match:
            return match.group(2).strip()
        return ""

    def _extract_section_block(self, text: str, headings: List[str]) -> str:
        lines = text.splitlines()
        capture = False
        buffer = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if capture and buffer:
                    break
                continue

            if any(stripped.lower().startswith(h) for h in headings):
                capture = True
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    buffer.append(parts[1].strip())
                continue

            if capture:
                if re.match(r"^[A-Z][A-Za-z\s]{1,40}:?$", stripped):
                    break
                buffer.append(stripped)

        return " ".join(buffer).strip()

    def _looks_like_name(self, value: str) -> bool:
        return len(value.split()) >= 2 and ":" not in value
