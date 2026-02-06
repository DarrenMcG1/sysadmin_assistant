"""Health check endpoint."""

from fastapi import APIRouter

from sysadmin import __version__

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check — confirms the service is running."""
    return {
        "status": "healthy",
        "service": "sysadmin-service",
        "version": __version__,
    }
