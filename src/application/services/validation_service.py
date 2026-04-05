from src.domain.cv.rules.completeness_rules import check_completeness


class ValidationService:
    def validate(self, cv_data: dict) -> dict:
        errors = check_completeness(cv_data)
        warnings = []
        suggestions = []

        summary = cv_data.get("summary", {}).get("professional_summary", "")
        skills = cv_data.get("skills", {}).get("primary_skills", [])

        if summary and len(summary.split()) < 8:
            warnings.append("Professional summary is very short.")
            suggestions.append("Expand the summary to 2–3 lines with role alignment and impact.")
        if skills and len(skills) < 3:
            warnings.append("Consider adding more key skills.")
            suggestions.append("Add frameworks, cloud platforms, and tools to strengthen the CV.")
        if not cv_data.get("leadership"):
            suggestions.append("Leadership information can improve senior-role CV quality.")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }
