import re


class TranscriptNormalizer:
    def normalize(self, transcript: str) -> str:
        cleaned = transcript.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
        return cleaned

    def apply_manual_correction(self, transcript: str, corrected_text: str | None = None) -> str:
        if corrected_text and corrected_text.strip():
            return self.normalize(corrected_text)
        return self.normalize(transcript)
