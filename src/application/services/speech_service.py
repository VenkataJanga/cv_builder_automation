from src.ai.factories.speech_factory import get_speech_provider
from src.infrastructure.parsers.transcript_normalizer import TranscriptNormalizer
from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser


class SpeechService:
    def __init__(self) -> None:
        self.provider = get_speech_provider()
        self.normalizer = TranscriptNormalizer()
        self.cv_parser = TranscriptCVParser()

    def transcribe(self, file_path: str, language: str | None = None) -> dict:
        raw_transcript = self.provider.transcribe_file(file_path=file_path, language=language)
        normalized = self.normalizer.normalize(raw_transcript)
        extracted_cv_data = self.cv_parser.parse(normalized)

        return {
            "raw_transcript": raw_transcript,
            "normalized_transcript": normalized,
            "requires_correction": len(normalized.split()) < 3,
            "extracted_cv_data": extracted_cv_data,
        }

    def correct_transcript(self, transcript: str, corrected_text: str | None = None) -> dict:
        final_text = self.normalizer.apply_manual_correction(transcript, corrected_text)
        extracted_cv_data = self.cv_parser.parse(final_text)

        return {
            "final_transcript": final_text,
            "fallback_to_text_edit": True,
            "extracted_cv_data": extracted_cv_data,
        }
