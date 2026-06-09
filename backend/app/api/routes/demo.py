"""Demo endpoints — public, no authentication required."""

from fastapi import APIRouter
from app.core.response import success_response, error_http
from app.services.demo_service import get_demo, list_demos, DEMO_CONFIGS

router = APIRouter()


@router.get("/list")
async def demo_list():
    """List available demos. No auth required."""
    demos = list_demos()
    return success_response(data={"demos": demos})


@router.get("/{demo_id}")
async def demo_detail(demo_id: str):
    """Get a demo's full backtest result. No auth required."""
    demo = get_demo(demo_id)
    if not demo:
        if demo_id not in DEMO_CONFIGS:
            raise error_http("resource.not_found", f"Demo '{demo_id}' not found", status_code=404)
        # Retry compute
        from app.services.demo_service import _compute_demo, _demo_cache
        result = _compute_demo(demo_id)
        if result:
            _demo_cache[demo_id] = result
            demo = result
        else:
            raise error_http("server.error", "Demo temporarily unavailable", status_code=503)
    return success_response(data=demo)
