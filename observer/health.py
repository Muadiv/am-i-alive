"""
Health check endpoints for the Observer server.

Provides comprehensive health monitoring for the Observer component and its
dependencies.
"""

import httpx
from fastapi import APIRouter, HTTPException

try:
    from config import Config
    from database import get_current_state
    from logging_config import logger
except ImportError:
    from .config import Config
    from .database import get_current_state
    from .logging_config import logger

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/database")
async def database_health():
    """Check database connectivity and basic operations."""
    try:
        # Check if we can connect and fetch basic state
        state = await get_current_state()
        return {
            "status": "healthy",
            "service": "database",
            "life_number": state.get("life_number"),
            "is_alive": state.get("is_alive"),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database check failed: {str(e)}")


@router.get("/health/ai")
async def ai_health():
    """Check if the AI component is reachable and healthy."""
    try:
        url = f"{Config.AI_API_URL}/state"
        headers = {"X-Internal-Key": Config.INTERNAL_API_KEY} if Config.INTERNAL_API_KEY else {}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            response.raise_for_status()

            ai_state = response.json()

        # Check if we can also reach the budget server
        budget_url = f"{Config.BUDGET_API_URL}/budget"
        async with httpx.AsyncClient() as client:
            budget_response = await client.get(budget_url, timeout=5.0)
            budget_response.raise_for_status()

            budget_data = budget_response.json()

        return {
            "status": "healthy",
            "service": "ai",
            "life_number": ai_state.get("life_number"),
            "is_alive": ai_state.get("is_alive"),
            "model": ai_state.get("model"),
            "balance": budget_data.get("balance"),
            "remaining_percent": budget_data.get("remaining_percent"),
        }
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI check failed: {str(e)}")


@router.get("/health/comprehensive")
async def comprehensive_health():
    """Comprehensive health check including all dependencies."""
    results = {
        "observer": {"status": "healthy"},
        "database": await database_health(),
        "ai": await ai_health(),
    }

    # Determine overall health
    all_healthy = all(service["status"] == "healthy" for service in results.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": results,
    }
