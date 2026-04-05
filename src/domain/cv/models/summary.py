from pydantic import BaseModel
from typing import Optional


class Summary(BaseModel):
    """
    Professional summary of the user.
    This will be used directly in CV and can be AI-enhanced later (MVP2).
    """

    professional_summary: str

    # Optional target role for customization
    target_role: Optional[str] = None