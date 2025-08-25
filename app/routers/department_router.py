from fastapi import APIRouter, Depends, Query, HTTPException
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.utils.s3_util import get_s3_company_review
from app.services.department_service import get_department_name_by_id, get_department_reviews
from app.config.errors import ErrorMessages
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.review_schema import DepartmentReviewResponse, DepartmentSummaryResponse
from app.services.department_service import analyze_department_review

router = APIRouter(prefix="/departments", tags=["department"])

@router.get(
    "/reviews",
    response_model=DepartmentReviewResponse,
    summary="부서별 리뷰 조회 API",
    description="""
    유저의 소속 회사에 맞는 CSV 파일에서 부서별 리뷰를 조회합니다.""",
)
def department_reviews(
    department_id: int = Query(..., alias="departmentId", description="부서 ID 예: 1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_department_reviews(db, department_id, current_user.company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=ErrorMessages.INVALID_DEPARTMENT_ID)
    

@router.get(
    "/summary",
    response_model=DepartmentSummaryResponse,
    summary="부서 리뷰 요약 & 리포트 API",
    description="90일 이내 부서 리뷰 데이터를 바탕으로 긍/부정 의견을 2개씩 조회하고, 리포트를 제공합니다.",
)
def department_review_summary(
    department_id: int = Query(..., alias="departmentId", description="부서 ID 예: 1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return analyze_department_review(db, department_id, current_user.company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=ErrorMessages.INVALID_DEPARTMENT_ID)
