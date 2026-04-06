from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class CVWorkflowState:
    session_id: str
    role: str | None = None
    current_question: str | None = None
    cv_data: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    retrieved_context: List[Dict[str, Any]] = field(default_factory=list)
    followup_question: str | None = None
    confidence: Dict[str, Any] = field(default_factory=dict)
