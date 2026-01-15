from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/hq/insights", tags=["hq-insights-mock"])

class Insight(BaseModel):
    title: str
    severity: str
    site_code: Optional[str] = None
    detail: Optional[dict] = None

class InsightResponse(BaseModel):
    items: List[Insight]

from apps.plant_backend.intelligence_engine import get_insights_for_plant

@router.get("/overview", response_model=InsightResponse)
def get_insights_overview():
    real_insights = get_insights_for_plant(window_days=14)
    # Convert dataclass Insight to Pydantic Insight
    items = []
    for ri in real_insights:
        items.append(Insight(
            title=ri.title,
            severity=ri.severity,
            site_code=ri.site_code,
            detail=ri.detail
        ))
    return InsightResponse(items=items)
