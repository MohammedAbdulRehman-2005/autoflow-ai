
from fastapi import APIRouter, Depends, Request

from backend.followup_engine.schemas import (
    FollowupRequest,
    FollowupResponse
)
from backend.followup_engine.service import (
    generate_questions
)
from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.core.rate_limit import limiter

router = APIRouter(
    prefix="/followup",
    tags=["Follow Up Engine"]
)


@router.post(
    "/questions",
    response_model=FollowupResponse
)
@limiter.limit("30/minute")
def get_questions(
    request: Request,
    payload: FollowupRequest,
    current_user: User = Depends(get_current_user),
):
    return generate_questions(
        payload.industry
    )

