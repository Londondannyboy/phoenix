"""
Health check endpoints for Phoenix Gateway.
"""

import os
from fastapi import APIRouter
from temporal_client import TemporalClientManager

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "phoenix-gateway",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - validates Temporal connection.

    Returns:
        Readiness status with Temporal connection info
    """
    try:
        client = await TemporalClientManager.get_client()

        return {
            "status": "ready",
            "temporal": {
                "connected": True,
                "namespace": os.getenv("TEMPORAL_NAMESPACE"),
                "task_queue": os.getenv("TEMPORAL_TASK_QUEUE", "phoenix-queue")
            }
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "temporal": {
                "connected": False,
                "error": str(e)
            }
        }
