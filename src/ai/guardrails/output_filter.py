class OutputFilter:
	_BLOCKED_TERMS = (
		"password=",
		"api_key",
		"secret_key",
		"private key",
	)

	def is_safe(self, text: str) -> bool:
		normalized = (text or "").lower()
		return not any(term in normalized for term in self._BLOCKED_TERMS)

	def sanitize(self, text: str) -> str:
		if self.is_safe(text):
			return text
		sanitized = text
		for term in self._BLOCKED_TERMS:
			sanitized = sanitized.replace(term, "[FILTERED]")
			sanitized = sanitized.replace(term.upper(), "[FILTERED]")
		return sanitized
