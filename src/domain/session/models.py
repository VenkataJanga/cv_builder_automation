from pydantic import BaseModel
from typing import Optional

class Session(BaseModel):
    session_id: str
    user_id: Optional[str]
    status: str
