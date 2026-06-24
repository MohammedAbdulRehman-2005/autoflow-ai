from fastapi import APIRouter

from backend.intent_parser.schemas import (
    IntentRequest,
    ClarificationResponse

)

from backend.intent_parser.service import (
     parse_user_intent,
     generate_followup_questions,
)

router = APIRouter(
    prefix="/ai",
    tags=["Intent Parser"]
)


@router.post(
    "/parse-intent",
    response_model=ClarificationResponse
)

def parse_intent(request : IntentRequest):

    intent = parse_user_intent(request.prompt)

    questions = generate_followup_questions(intent)

    return{
         "workflow":intent,
         "need_clarification":len(questions)>0,
         "questions": questions
        }
