import os
import httpx
from openai import OpenAI
from src.core.config.settings import settings


class WhisperSpeechProvider:
    def __init__(self) -> None:
        # By default verify SSL. To bypass in dev, set OPENAI_VERIFY_SSL=false
        verify_ssl = settings.OPENAI_VERIFY_SSL

        if verify_ssl:
            # Secure client (verification ON)
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            # DEVELOPMENT-ONLY: disable SSL verification (insecure, do NOT use in production)
            import warnings
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            httpx_client = httpx.Client(verify=False)
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY, http_client=httpx_client)

    def transcribe_file(self, file_path: str, language: str | None = None) -> str:
        with open(file_path, "rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model=settings.WHISPER_MODEL,
                file=audio_file,
                language=language or "en",
            )
        return getattr(result, "text", str(result))
