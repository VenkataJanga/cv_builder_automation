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

        # Use continuous recognition for long-form audio (10+ minutes)
        all_results = []
        done = False
        
        def handle_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                all_results.append(evt.result.text)
        
        def handle_session_stopped(evt):
            nonlocal done
            done = True
        
        recognizer.recognized.connect(handle_recognized)
        recognizer.session_stopped.connect(handle_session_stopped)
        recognizer.canceled.connect(handle_session_stopped)
        
        recognizer.start_continuous_recognition()
        
        # Wait for completion (with timeout for safety)
        import time
        timeout = 600  # 10 minutes max
        start_time = time.time()
        while not done and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        recognizer.stop_continuous_recognition()
        
        return " ".join(all_results)
