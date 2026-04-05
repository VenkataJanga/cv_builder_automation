from pydantic import BaseModel
from typing import Optional

class Education(BaseModel):
    degree: str
    institution: str
    year_of_completion: Optional[int] = None
