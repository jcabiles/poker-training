"""API v1 router. Sub-routers are included here as tickets land."""

from fastapi import APIRouter

from app.api.v1.drill import router as drill_router
from app.api.v1.stats import router as stats_router

router = APIRouter()


@router.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(drill_router)
router.include_router(stats_router)
