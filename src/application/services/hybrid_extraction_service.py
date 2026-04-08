from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.infrastructure.parsers.resume_parser import ResumeParser
from src.infrastructure.parsers.transcript_cv_parser_fixed import TranscriptCVParser
from src.ai.services.voice_transcript_production_extractor import extract_from_voice_transcript


class HybridExtractionService:
    def __init__(self) -> None:
        self.resume_parser = ResumeParser()
        self.transcript_parser = TranscriptCVParser()
        self.enhancement_service = LLMEnhancementService()

    def extract_from_resume_text(self, text: str, role: str | None = None) -> dict:
        parsed = self.resume_parser.parse(text)
        if self.resume_parser.low_confidence(parsed):
            parsed = self.enhancement_service.enhance_cv_sections(parsed, role=role)
        return parsed

    def extract_from_transcript(self, text: str, role: str | None = None) -> dict:
        parsed = self.transcript_parser.parse(text)
        if self.transcript_parser.low_confidence(parsed):
            parsed = self.enhancement_service.enhance_cv_sections(parsed, role=role)
        return parsed
    
    def extract_from_voice(self, transcript: str, initial_data: dict | None = None) -> dict:
        """
        Extract CV data from voice transcript using production-grade extractor
        
        Args:
            transcript: Voice transcript text
            initial_data: Optional initial data to merge with
            
        Returns:
            Extracted CV data with proper project extraction
        """
        # Use the production-grade voice transcript extractor
        parsed = extract_from_voice_transcript(transcript)
        
        # Merge with initial data if provided
        if initial_data:
            # Simple merge - prioritize voice extraction for new fields
            for key, value in parsed.items():
                if value and (key not in initial_data or not initial_data[key]):
                    initial_data[key] = value
            parsed = initial_data
        
        # Check if enhancement is needed (low confidence on projects)
        project_experience = parsed.get("project_experience", [])
        if not project_experience or len(project_experience) == 0:
            # Fall back to basic parser and then enhance if needed
            fallback_parsed = self.transcript_parser.parse(transcript)
            if fallback_parsed.get("project_experience"):
                parsed["project_experience"] = fallback_parsed["project_experience"]
            
            # Enhance if still low confidence
            if self._needs_enhancement(parsed):
                parsed = self.enhancement_service.enhance_cv_sections(parsed)
        
        return parsed
    
    def _needs_enhancement(self, parsed_data: dict) -> bool:
        """Check if the parsed data needs LLM enhancement"""
        # Check project completeness
        projects = parsed_data.get("project_experience", [])
        if not projects:
            return True
            
        # Check if projects have essential fields
        for project in projects:
            if not project.get("project_name") or not project.get("project_description"):
                return True
        
        return False
