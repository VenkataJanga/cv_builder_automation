class LangSmithService:
    def trace(self, run_name: str, payload: dict) -> dict:
        return {
            "langsmith_enabled": False,
            "run_name": run_name,
            "payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
        }
