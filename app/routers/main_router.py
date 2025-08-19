from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.services.main_service import get_company_statistics, get_quarterly_summary
from app.config.database import get_db
from app.schemas.review_schema import CompanyQuarterSummaryResponse

router = APIRouter(prefix="/main", tags=["main"])

@router.get("/statistics")
def company_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_company_statistics(current_user)

@router.get(
    "/summary",
    response_model=CompanyQuarterSummaryResponse,
    summary="분기별 리포트 조회 API",
    description="""
    유저의 소속 회사에 맞춰 분기별 리포트를 제공합니다.""",
)
def quarterly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_quarterly_summary(current_user)
