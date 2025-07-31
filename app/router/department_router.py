from fastapi import APIRouter, Depends, Query, HTTPException
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.utils.s3_util import get_s3_csv_key
from app.services.department_service import get_department_reviews

router = APIRouter(prefix="/department", tags=["department"])

@router.get("/reviews")
def department_reviews(
    department: str = Query(..., description="부서명 예: 마케팅팀 (Marketing)"),
    current_user: User = Depends(get_current_user)
):
    s3_key, _ = get_s3_csv_key(current_user)
    try:
        return get_department_reviews(s3_key, department)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
