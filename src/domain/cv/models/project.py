from pydantic import BaseModel
from typing import List, Optional

class ProjectExperience(BaseModel):
    project_name: str
    role: str
    technologies: List[str] = []
    responsibilities: List[str] = []
    outcomes: List[str] = []
