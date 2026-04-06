from src.ai.factories.speech_factory import get_speech_provider
from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.infrastructure.parsers.transcript_normalizer import TranscriptNormalizer
from src.infrastructure.parsers.transcript_cv_parser_fixed import TranscriptCVParser
from src.infrastructure.parsers.enhanced_transcript_parser import EnhancedTranscriptParser


class SpeechService:
    def __init__(self) -> None:
        self.provider = get_speech_provider()
        self.normalizer = TranscriptNormalizer()
        self.llm_enhancement_service = LLMEnhancementService()
        self.cv_parser = TranscriptCVParser()  # Keep for fallback
        self.enhanced_parser = EnhancedTranscriptParser()  # New structured parser

    def transcribe(self, file_path: str, language: str | None = None) -> dict:
        raw_transcript = self.provider.transcribe_file(file_path=file_path, language=language)
        normalized = self.normalizer.normalize(raw_transcript)

        enhancement_result = self.llm_enhancement_service.enhance_transcript(normalized)
        enhanced_transcript = enhancement_result["enhanced_transcript"]

        # Use the new enhanced parser for structured transcripts
        extracted_cv_data = self._extract_cv_data(enhanced_transcript)

        return {
            "raw_transcript": raw_transcript,
            "normalized_transcript": normalized,
            "enhanced_transcript": enhanced_transcript,
            "requires_correction": len(normalized.split()) < 3,
            "extracted_cv_data": extracted_cv_data,
        }

    def correct_transcript(self, transcript: str, corrected_text: str | None = None) -> dict:
        final_text = self.normalizer.apply_manual_correction(transcript, corrected_text)

        enhancement_result = self.llm_enhancement_service.enhance_transcript(final_text)
        enhanced_transcript = enhancement_result["enhanced_transcript"]

        # Use the new enhanced parser for structured transcripts
        extracted_cv_data = self._extract_cv_data(enhanced_transcript)

        return {
            "final_transcript": final_text,
            "enhanced_transcript": enhanced_transcript,
            "fallback_to_text_edit": True,
            "extracted_cv_data": extracted_cv_data,
        }

    def _extract_cv_data(self, enhanced_transcript: str) -> dict:
        """
        Extract CV data using the appropriate parser based on transcript structure.
        Uses enhanced parser for structured transcripts, falls back to original parser.
        """
        # Try the enhanced parser first for structured transcripts
        if self._is_structured_transcript(enhanced_transcript):
            extracted_data = self.enhanced_parser.parse(enhanced_transcript)
            
            # Check if extraction was successful
            if not self.enhanced_parser.low_confidence(extracted_data):
                return extracted_data
        
        # Fallback to original parser for unstructured text
        return self.cv_parser.parse(enhanced_transcript)
    
    def _is_structured_transcript(self, transcript: str) -> bool:
        """
        Check if the transcript has structured markdown-like formatting
        that the enhanced parser can handle.
        """
        structure_indicators = [
            "**Professional Summary**",
            "**Core Competencies**", 
            "**Industry Experience**",
            "**Project Experience**",
            "**Education**",
            "Portal ID:",
            "Grade:",
            "Contact:",
            "Email:"
        ]
        
        # Count how many structure indicators are present
        indicators_found = sum(1 for indicator in structure_indicators 
                             if indicator in transcript)
        
        # If we find 3 or more structure indicators, treat as structured
        return indicators_found >= 3
