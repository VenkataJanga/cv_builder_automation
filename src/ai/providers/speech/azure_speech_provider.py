from src.ai.providers.speech.base import BaseSpeechProvider
from src.core.config.settings import settings


class AzureSpeechProvider(BaseSpeechProvider):
    def transcribe_file(self, file_path: str, language: str | None = None) -> str:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except Exception as e:
            raise RuntimeError("Install azure-cognitiveservices-speech package") from e

        if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
            raise RuntimeError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION are not configured")

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION,
        )
        speech_config.speech_recognition_language = language or settings.AZURE_SPEECH_LANGUAGE

        audio_config = speechsdk.audio.AudioConfig(filename=file_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text or ""
        if result.reason == speechsdk.ResultReason.NoMatch:
            return ""
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            raise RuntimeError(f"Azure Speech canceled: {cancellation.reason}")

        return ""
