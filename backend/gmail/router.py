from fastapi import APIRouter

from backend.gmail.service import (
    send_test_email
)

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)


@router.post("/test-send")
def test_send():

    return send_test_email(
        "test@gmail.com"
    )
