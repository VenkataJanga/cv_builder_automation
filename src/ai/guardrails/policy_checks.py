from src.ai.guardrails.output_filter import OutputFilter
from src.ai.guardrails.pii_guard import PIIGuard
from src.ai.guardrails.prompt_injection_guard import PromptInjectionGuard


class GuardrailPolicyChecks:
	def __init__(self) -> None:
		self.pii_guard = PIIGuard()
		self.injection_guard = PromptInjectionGuard()
		self.output_filter = OutputFilter()

	def validate_prompt(self, prompt: str) -> None:
		self.injection_guard.assert_safe(prompt)

	def sanitize_output(self, output: str) -> str:
		filtered = self.output_filter.sanitize(output)
		return self.pii_guard.redact(filtered)
