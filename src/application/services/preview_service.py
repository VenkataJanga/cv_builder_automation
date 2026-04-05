from src.ai.agents.cv_formatting_agent import CVFormattingAgent


class PreviewService:
    def __init__(self) -> None:
        self.formatter = CVFormattingAgent()

    def build_preview(self, cv_data: dict) -> dict:
        return self.formatter.format_cv(cv_data)
