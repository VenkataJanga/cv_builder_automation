from src.ai.providers.speech.azure_speech_provider import AzureSpeechProvider
from src.ai.providers.speech.base import BaseSpeechProvider
from src.ai.providers.speech.whisper_speech_provider import WhisperSpeechProvider
from src.core.config.settings import settings


def get_speech_provider() -> BaseSpeechProvider:
    provider = settings.SPEECH_PROVIDER.lower().strip()
    if provider == "azure":
        return AzureSpeechProvider()
    return WhisperSpeechProvider()
