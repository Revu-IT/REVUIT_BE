from fastapi import APIRouter, Depends, Query, HTTPException
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.utils.s3_util import get_s3_company_review
from app.services.department_service import get_department_name_by_id, get_department_reviews
from app.config.errors import ErrorMessages
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.review_schema import DepartmentReviewResponse

router = APIRouter(prefix="/departments", tags=["department"])

@router.get(
    "/reviews",
    response_model=DepartmentReviewResponse,
    summary="부서별 리뷰 조회",
    description="""
    유저의 소속 회사에 맞는 CSV 파일에서 부서별 리뷰를 조회합니다.
    - departmentId: 조회할 부서의 ID입니다.
    - 로그인한 유저의 company_id 기준으로 CSV 파일이 선택됩니다.
    """,
)
def department_reviews(
    department_id: int = Query(..., alias="departmentId", description="부서 ID 예: 1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s3_key = get_s3_company_review(current_user)

    try:
        department_name = get_department_name_by_id(db, department_id)
        return get_department_reviews(s3_key, department_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=ErrorMessages.INVALID_DEPARTMENT_ID)
    

