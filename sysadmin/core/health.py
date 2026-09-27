"""Health check endpoint, served at two paths.

``/api/health`` is the path the monitorable-project contract requires of
every service on this box, and the one ``services.yaml`` polls for this
one. ``/health`` is kept because the tray's liveness probe requests it
(``sysadmin_tray/client.py``). One handler under both, so the two cannot
answer differently.
"""

from fastapi import APIRouter

from sysadmin import __version__
from sysadmin.core.contracts import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Basic health check — confirms the service is running."""
    return {
        "status": "healthy",
        "service": "sysadmin-service",
        "version": __version__,
    }
