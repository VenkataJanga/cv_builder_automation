from pydantic import BaseModel
from typing import Optional


class BasicProfile(BaseModel):
    """
    Core personal information required to identify the user
    and seed the CV generation flow.
    """

    full_name: str
    current_title: str
    location: str

    # Optional profile/contact fields for MVP1.
    total_experience: Optional[float] = None
    current_organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None