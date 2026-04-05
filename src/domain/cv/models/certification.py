from pydantic import BaseModel
from typing import Optional

class Certification(BaseModel):
    certification_name: str
    issuing_organization: Optional[str] = None
