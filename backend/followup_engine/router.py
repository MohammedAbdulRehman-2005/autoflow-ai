
from fastapi import APIRouter

from backend.followup_engine.schemas import (
    FollowupRequest,
    FollowupResponse
)

from backend.followup_engine.service import (
    generate_questions
)

router = APIRouter(
    prefix="/followup",
    tags=["Follow Up Engine"]
)


@router.post(
    "/questions",
    response_model=FollowupResponse
)
def get_questions(
    request: FollowupRequest
):

    return generate_questions(
        request.industry
    )
