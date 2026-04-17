class PromptInjectionGuard:
	_BLOCKLIST = (
		"ignore previous instructions",
		"system prompt",
		"reveal hidden prompt",
		"bypass policy",
		"execute shell",
	)

	def is_suspicious(self, text: str) -> bool:
		normalized = (text or "").lower()
		return any(token in normalized for token in self._BLOCKLIST)

	def assert_safe(self, text: str) -> None:
		if self.is_suspicious(text):
			raise ValueError("Prompt blocked by injection guard")
