
from pydantic import BaseModel


class IntentRequest(BaseModel):
    prompt: str


class IntentResponse(BaseModel):
    industry: str
    goal: str
    confidence: float
