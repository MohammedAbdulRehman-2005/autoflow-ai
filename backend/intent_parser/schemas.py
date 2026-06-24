
from pydantic import BaseModel
from typing import List,Optional

class IntentRequest(BaseModel):
    prompt: str


class ClarificationResponse(BaseModel):
    workflow:dict
    need_clarification:bool
    questions:List[str]=[]
