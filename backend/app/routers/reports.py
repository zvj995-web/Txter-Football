from fastapi import APIRouter, Query

from app.models.reports import ReportOut
from app.services.report_service import list_reports

router = APIRouter(tags=["Reports"])


@router.get("/reports", response_model=list[ReportOut])
def get_reports(
    keyword: str = Query(""),
    fromHours: float | None = Query(None, ge=-50, le=100),
    toHours: float | None = Query(None, ge=-50, le=100),
):
    return list_reports(keyword, from_hours=fromHours, to_hours=toHours)
