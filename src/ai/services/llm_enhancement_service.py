from src.ai.agents.enhancement_agent import EnhancementAgent


class LLMEnhancementService:
    def __init__(self) -> None:
        self.agent = EnhancementAgent()

    def enhance_transcript(self, normalized_transcript: str) -> dict:
        # Use structure_cv_transcript so the output has the exact section headers
        # that CanonicalAudioParser's markdown extraction path relies on.  If the
        # LLM call fails the method falls back to basic text cleanup internally.
        enhanced = self.agent.structure_cv_transcript(normalized_transcript)
        return {
            "normalized_transcript": normalized_transcript,
            "enhanced_transcript": enhanced,
        }

    def enhance_cv_sections(self, cv_data: dict, role: str = None) -> dict:
        """
        Enhance specific sections of CV data using LLM.
        Only enhances sections that need improvement.
        """
        enhanced_data = cv_data.copy()

        # Enhance summary if present
        if cv_data.get("summary"):
            if isinstance(cv_data["summary"], dict) and cv_data["summary"].get("professional_summary"):
                summary_text = cv_data["summary"]["professional_summary"]
                enhanced_summary = self.agent.enhance_summary_text(summary_text, role)
                enhanced_data["summary"] = {"professional_summary": enhanced_summary}
            elif isinstance(cv_data["summary"], str):
                enhanced_summary = self.agent.enhance_summary_text(cv_data["summary"], role)
                enhanced_data["summary"] = {"professional_summary": enhanced_summary}

        # Enhance project descriptions if present
        if cv_data.get("project_experience"):
            enhanced_projects = []
            for project in cv_data["project_experience"]:
                if isinstance(project, dict) and project.get("project_description"):
                    enhanced_desc = self.agent.enhance_achievement_text(project["project_description"])
                    enhanced_project = project.copy()
                    enhanced_project["project_description"] = enhanced_desc
                    enhanced_projects.append(enhanced_project)
                else:
                    enhanced_projects.append(project)
            enhanced_data["project_experience"] = enhanced_projects

        return enhanced_data
