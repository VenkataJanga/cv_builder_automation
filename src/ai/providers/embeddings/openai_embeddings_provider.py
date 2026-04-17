import httpx
from openai import OpenAI

from src.core.config.settings import settings
from src.ai.providers.embeddings.base import BaseEmbeddingsProvider


class OpenAIEmbeddingsProvider(BaseEmbeddingsProvider):
	def __init__(self) -> None:
		verify_ssl = settings.OPENAI_VERIFY_SSL
		timeout = httpx.Timeout(30.0, connect=10.0)

		if verify_ssl:
			self.client = OpenAI(
				api_key=settings.OPENAI_API_KEY,
				timeout=timeout,
				max_retries=2,
			)
		else:
			httpx_client = httpx.Client(verify=False, timeout=timeout)
			self.client = OpenAI(
				api_key=settings.OPENAI_API_KEY,
				http_client=httpx_client,
				max_retries=2,
			)

		self.model = settings.OPENAI_EMBEDDING_MODEL

	def embed_text(self, text: str) -> list[float]:
		response = self.client.embeddings.create(model=self.model, input=text)
		return response.data[0].embedding

	def embed_texts(self, texts: list[str]) -> list[list[float]]:
		response = self.client.embeddings.create(model=self.model, input=texts)
		return [item.embedding for item in response.data]
