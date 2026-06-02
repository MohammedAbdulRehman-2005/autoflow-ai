from pydantic import BaseModel


class FollowupRequest(BaseModel):
    industry: str


class Question(BaseModel):
    id: str
    text: str
    type: str


class FollowupResponse(BaseModel):
    questions: list[Question]
