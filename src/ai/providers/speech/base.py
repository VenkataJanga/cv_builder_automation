from abc import ABC, abstractmethod


class BaseSpeechProvider(ABC):
    @abstractmethod
    def transcribe_file(self, file_path: str, language: str | None = None) -> str:
        raise NotImplementedError
