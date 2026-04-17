from typing import Sequence


class BaseEmbeddingsProvider:
	def embed_text(self, text: str) -> list[float]:
		raise NotImplementedError

	def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
		raise NotImplementedError
