from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserResponse, UserLogin, Token
from app.services.user_service import signup_user, login_user, get_current_user, get_my_info

router = APIRouter(prefix="/user", tags=["user"])

# 회원가입
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: UserCreate, db: Session = Depends(get_db)):
    return signup_user(db, data)

# 로그인
@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(data: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, data)

# 마이페이지
@router.get("/mypage", response_model=UserResponse, status_code=status.HTTP_200_OK)
def mypage(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_my_info(current_user)