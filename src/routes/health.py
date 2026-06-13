from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Health Check", tags=["System"])
async def health_check() -> dict:
    """
    Returns a simple status response.
    Visit http://localhost:8000/ to confirm the server is running.
    """
    return {
        "status": "ok",
        "message": "AI Code Review Agent is running!",
    }
