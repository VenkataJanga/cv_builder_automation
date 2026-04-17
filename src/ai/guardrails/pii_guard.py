import re


class PIIGuard:
	EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
	PHONE_RE = re.compile(r"(?:\\+?\\d{1,3}[ -]?)?(?:\\d[ -]?){10,}")

	def redact(self, text: str) -> str:
		redacted = self.EMAIL_RE.sub("[REDACTED_EMAIL]", text or "")
		redacted = self.PHONE_RE.sub("[REDACTED_PHONE]", redacted)
		return redacted

	def contains_pii(self, text: str) -> bool:
		if not text:
			return False
		return bool(self.EMAIL_RE.search(text) or self.PHONE_RE.search(text))
