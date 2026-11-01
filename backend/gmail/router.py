from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)


@router.post("/test-send")
def test_send(email: str):
    """Disabled endpoint. Unauthenticated email sending is prohibited."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="The /test-send endpoint is disabled for security containment. Unauthenticated email sending is not permitted."
    )

