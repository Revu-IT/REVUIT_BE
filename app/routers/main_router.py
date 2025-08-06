from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.services.user_service import get_current_user
from app.services.main_service import get_company_statistics
from app.config.database import get_db

router = APIRouter(prefix="/main", tags=["main"])

@router.get("/statistics")
def company_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_company_statistics(current_user)
