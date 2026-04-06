from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.infrastructure.parsers.resume_parser import ResumeParser
from src.infrastructure.parsers.transcript_cv_parser_fixed import TranscriptCVParser


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
