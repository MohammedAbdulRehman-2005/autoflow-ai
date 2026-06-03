from fastapi import APIRouter

from backend.intent_parser.schemas import (
    IntentRequest,
    IntentResponse
)

from backend.intent_parser.service import (
    parse_user_intent
)

router = APIRouter(
    prefix="/ai",
    tags=["Intent Parser"]
)


@router.post(
    "/parse-intent",
    response_model=IntentResponse
)
def parse_intent(
    request: IntentRequest
):

    return parse_user_intent(
        request.prompt
    )
