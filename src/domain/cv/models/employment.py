from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class WorkExperience(BaseModel):
    company_name: str
    role_title: str
    start_date: date
    end_date: Optional[date] = None
    responsibilities: List[str] = []
    achievements: List[str] = []
