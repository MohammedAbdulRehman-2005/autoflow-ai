from fastapi import APIRouter, Depends, Request

from backend.intent_parser.schemas import (
    IntentRequest,
    ClarificationResponse
)

from backend.intent_parser.service import parse_user_intent
from backend.intent_parser.gemini_followup import generate_followup_questions
from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.core.rate_limit import limiter

router = APIRouter(
    prefix="/ai",
    tags=["Intent Parser"]
)


@router.post(
    "/parse-intent",
    response_model=ClarificationResponse
)
@limiter.limit("20/minute")
def parse_intent(
    request: Request,
    payload: IntentRequest,
    current_user: User = Depends(get_current_user),
):

    intent = parse_user_intent(payload.prompt)

    questions = generate_followup_questions(payload.prompt, intent)


    return{
         "workflow":intent,
         "need_clarification":len(questions)>0,
         "questions": questions
        }
