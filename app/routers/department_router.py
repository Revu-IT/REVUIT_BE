from fastapi import APIRouter, Depends, Query, HTTPException
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.utils.s3_util import get_s3_company_review
from app.services.department_service import get_department_name_by_id, get_department_reviews
from app.config.errors import ErrorMessages
from sqlalchemy.orm import Session
from app.config.database import get_db

router = APIRouter(prefix="/departments", tags=["department"])

@router.get("/reviews")
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
    

