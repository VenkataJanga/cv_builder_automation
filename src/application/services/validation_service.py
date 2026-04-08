from src.domain.cv.rules.completeness_rules import check_completeness
from src.domain.cv.rules.chronology_rules import check_chronology
from src.domain.cv.rules.duplication_rules import check_duplicates
from src.domain.cv.rules.quality_rules import check_quality


class ValidationService:
    def validate(self, cv_data: dict) -> dict:
        errors = []
        errors.extend(check_completeness(cv_data))
        errors.extend(check_chronology(cv_data))
        errors.extend(check_duplicates(cv_data))

        quality = check_quality(cv_data)

        summary_text = self._extract_summary_text(cv_data)
        
        # Handle skills as list or dict
        skills = cv_data.get("skills", {})
        skills_present = False
        if isinstance(skills, list):
            skills_present = bool(skills)
        elif isinstance(skills, dict):
            skills_present = bool(skills.get("primary_skills"))
        
        section_scores = {
            "summary_score": 100 if summary_text else 0,
            "skills_score": 100 if skills_present else 0,
            "leadership_score": 100 if cv_data.get("leadership") else 40,
        }

        confidence = self._compute_confidence(cv_data)
        
        # Compute overall validation score (0-100)
        all_issues = errors + quality.get("warnings", [])
        score = max(0, 100 - (len(errors) * 15) - (len(quality.get("warnings", [])) * 5))

        return {
            "is_valid": len(errors) == 0,
            "score": score,
            "issues": all_issues,
            "errors": errors,
            "warnings": quality.get("warnings", []),
            "suggestions": quality.get("suggestions", []),
            "section_scores": section_scores,
            "confidence": confidence,
        }

    def _compute_confidence(self, cv_data: dict) -> dict:
        personal = cv_data.get("personal_details", {})
        skills = cv_data.get("skills", {})
        summary = self._extract_summary_text(cv_data)
        leadership = cv_data.get("leadership", {})
        
        personal_score = 90 if personal else 30
        skills_score = 90 if skills.get("primary_skills") else 20
        summary_score = 85 if summary else 25
        leadership_score = 80 if leadership else 40
        
        overall_score = (personal_score + skills_score + summary_score + leadership_score) / 4
        
        return {
            "personal_details_confidence": personal_score / 100,
            "skills_confidence": skills_score / 100,
            "summary_confidence": summary_score / 100,
            "leadership_confidence": leadership_score / 100,
            "overall_score": overall_score,
        }

    def _extract_summary_text(self, cv_data: dict) -> str:
        summary = cv_data.get("summary", "")
        if isinstance(summary, dict):
            return str(summary.get("professional_summary", "")).strip()
        if isinstance(summary, list):
            parts = []
            for item in summary:
                if isinstance(item, dict):
                    parts.append(str(item.get("professional_summary", "")).strip())
                else:
                    parts.append(str(item).strip())
            return " ".join([part for part in parts if part]).strip()
        return str(summary).strip()
