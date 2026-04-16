from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.infrastructure.parsers.resume_parser import ResumeParser
from src.infrastructure.parsers.transcript_cv_parser_fixed import TranscriptCVParser
from src.ai.services.voice_transcript_production_extractor import extract_from_voice_transcript
from src.ai.services.conversational_text_extractor import extract_from_conversational_text


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
        Extract CV data from voice transcript or conversational text
        
        Args:
            transcript: Voice transcript or conversational text
            initial_data: Optional initial data to merge with
            
        Returns:
            Extracted CV data with proper field extraction
        """
        # Determine if this is a voice transcript or conversational text
        if self._is_voice_transcript(transcript):
            # Use the production-grade voice transcript extractor
            parsed = extract_from_voice_transcript(transcript)
        else:
            # Use conversational text extractor for natural conversation
            parsed = extract_from_conversational_text(transcript)
        
        # Merge with initial data if provided
        if initial_data:
            # Simple merge - prioritize new extraction for new fields
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
    
    def _is_voice_transcript(self, text: str) -> bool:
        """
        Determine if text is a voice transcript or conversational input
        
        Voice transcripts typically have specific patterns like:
        - "my name is john smith. my portal id is..."
        - "coming to my educational background..."
        - "my first project is..."
        
        Conversational text is more natural:
        - "My name is John Smith. My phone number is +1-555-123-4567..."
        - "I'm located in New York, NY and work at..."
        """
        text_lower = text.lower()
        
        # Voice transcript indicators
        voice_indicators = [
            "coming to my educational",
            "my first project is",
            "my second project",
            "coming to my roles and responsibilities",
            "over the course of my career",
            "over past",
            "clients such as"
        ]
        
        # Conversational text indicators  
        conversational_indicators = [
            "my phone number is",
            "portal id is",
            "i'm located in",
            "i currently work at",
            "my primary skills include",
            "my secondary skills are",
            "bachelor's degree",
            "master's degree",
            "years of experience"
        ]
        
        voice_score = sum(1 for indicator in voice_indicators if indicator in text_lower)
        conversational_score = sum(1 for indicator in conversational_indicators if indicator in text_lower)
        
        # If we have more conversational indicators, treat as conversational
        # If we have voice indicators, treat as voice transcript
        # Default to conversational for mixed/unclear cases
        return voice_score > conversational_score and voice_score > 0

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
