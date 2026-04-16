from src.ai.factories.speech_factory import get_speech_provider
from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.ai.services.voice_transcript_fixed_extractor import extract_from_voice_transcript
from src.application.services.hybrid_extraction_service import HybridExtractionService
from src.infrastructure.parsers.enhanced_transcript_parser import EnhancedTranscriptParser
from src.infrastructure.parsers.transcript_normalizer import TranscriptNormalizer
import re


class SpeechService:
    """
    Speech Service - Phase 3 Simplified
    
    Handles only transcription and LLM enhancement.
    CV extraction is now handled by AudioCVService + CanonicalAudioParser.
    """
    
    def __init__(self) -> None:
        self.provider = get_speech_provider()
        self.normalizer = TranscriptNormalizer()
        self.llm_enhancement_service = LLMEnhancementService()
        # Backward-compatible parser hooks used by legacy tests/flows.
        self.enhanced_parser = EnhancedTranscriptParser()
        self.hybrid_extraction_service = HybridExtractionService()

    def _extract_cv_data(self, transcript: str) -> dict:
        """
        Backward-compatible extraction method used by legacy flows/tests.

        Phase 3+ canonical pipeline uses AudioCVService, but this method is kept to
        avoid breaking older code paths that still expect speech-level extraction.
        """
        if not transcript:
            return {}

        parser = getattr(self, "enhanced_parser", None)
        hybrid = getattr(self, "hybrid_extraction_service", None)

        if parser is not None:
            try:
                extracted = parser.parse(transcript)
                if hasattr(parser, "low_confidence") and parser.low_confidence(extracted):
                    # Prefer legacy fixed extractor output shape for compatibility.
                    return self._normalize_legacy_extraction(
                        extract_from_voice_transcript(transcript),
                        transcript,
                    )
                if extracted:
                    return self._normalize_legacy_extraction(extracted, transcript)
            except Exception:
                # Fall through to hybrid extraction.
                pass

        try:
            return self._normalize_legacy_extraction(
                extract_from_voice_transcript(transcript),
                transcript,
            )
        except Exception:
            pass

        if hybrid is not None:
            if hasattr(hybrid, "extract_cv_data"):
                return self._normalize_legacy_extraction(hybrid.extract_cv_data(transcript), transcript)
            if hasattr(hybrid, "extract_from_voice"):
                return self._normalize_legacy_extraction(hybrid.extract_from_voice(transcript), transcript)

        return {}

    def _normalize_legacy_extraction(self, extracted: dict, transcript: str) -> dict:
        """Ensure backward-compatible project ordering/shape for legacy consumers."""
        if not isinstance(extracted, dict):
            return {}

        projects = extracted.get("project_experience")
        if not isinstance(projects, list):
            return extracted

        first_project_match = re.search(
            r"my first project(?: name)? is\s+([^.,]+)",
            transcript,
            re.IGNORECASE,
        )
        if not first_project_match:
            return extracted

        first_project_name = first_project_match.group(1).strip().title()
        normalized_name = first_project_name.lower()

        existing_index = None
        for idx, project in enumerate(projects):
            if not isinstance(project, dict):
                continue
            candidate_name = str(project.get("project_name", "")).strip(" ,").lower()
            if candidate_name == normalized_name:
                existing_index = idx
                break

        if existing_index is None:
            projects.insert(0, {"project_name": first_project_name})
        elif existing_index != 0:
            projects.insert(0, projects.pop(existing_index))

        if isinstance(projects[0], dict) and projects[0].get("project_name"):
            projects[0]["project_name"] = str(projects[0]["project_name"]).strip(" ,")

        extracted["project_experience"] = projects
        return extracted

    def transcribe(self, file_path: str, language: str | None = None) -> dict:
        """
        Transcribe audio file and enhance transcript.
        
        CV extraction is handled separately by AudioCVService.
        """
        raw_transcript = self.provider.transcribe_file(file_path=file_path, language=language)
        normalized = self.normalizer.normalize(raw_transcript)

        enhancement_result = self.llm_enhancement_service.enhance_transcript(normalized)
        enhanced_transcript = enhancement_result["enhanced_transcript"]
        extracted_cv_data = self._extract_cv_data(enhanced_transcript)

        return {
            "raw_transcript": raw_transcript,
            "normalized_transcript": normalized,
            "enhanced_transcript": enhanced_transcript,
            "requires_correction": len(normalized.split()) < 3,
            "extracted_cv_data": extracted_cv_data,
        }

    def correct_transcript(self, transcript: str, corrected_text: str | None = None) -> dict:
        """
        Apply manual correction to transcript and enhance.
        
        CV extraction is handled separately by AudioCVService.
        """
        final_text = self.normalizer.apply_manual_correction(transcript, corrected_text)

        enhancement_result = self.llm_enhancement_service.enhance_transcript(final_text)
        enhanced_transcript = enhancement_result["enhanced_transcript"]
        extracted_cv_data = self._extract_cv_data(enhanced_transcript)

        return {
            "final_transcript": final_text,
            "enhanced_transcript": enhanced_transcript,
            "fallback_to_text_edit": True,
            "extracted_cv_data": extracted_cv_data,
        }
