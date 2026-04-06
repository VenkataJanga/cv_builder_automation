from src.ai.agents.enhancement_agent import EnhancementAgent


class LLMEnhancementService:
    def __init__(self) -> None:
        self.agent = EnhancementAgent()

    def enhance_transcript(self, normalized_transcript: str) -> dict:
        enhanced = self.agent.professionalize_transcript_text(normalized_transcript)
        return {
            "normalized_transcript": normalized_transcript,
            "enhanced_transcript": enhanced,
        }
