from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserResponse, UserLogin, Token, UserUpdate
from app.services.user_service import signup_user, login_user, get_current_user, get_my_info, update_user_info

router = APIRouter(prefix="/user", tags=["user"])

@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입 API",
    description="""
    신규 사용자 회원가입을 위한 API입니다.  
    회원 정보를 입력하면 계정이 생성되고, 생성된 사용자 정보를 반환합니다.
    """
)
def signup(data: UserCreate, db: Session = Depends(get_db)):
    return signup_user(db, data)

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="로그인 API",
    description="""
    기존 사용자 로그인을 위한 API입니다.
    이메일과 비밀번호를 입력하면 JWT 토큰을 반환합니다.
    """
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, data)

@router.get(
    "/mypage",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="마이페이지 조회 API",
    description="""
    현재 로그인된 사용자의 기본 정보를 조회하는 API입니다.  
    JWT 인증 토큰이 필요하며, 회원의 상세 정보를 반환합니다.
    """
)
def mypage(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_my_info(current_user)

@router.put(
    "/mypage/update",
    response_model=UserResponse,
    summary="회원 정보 수정 API",
    description="""
    현재 로그인된 사용자의 정보를 수정하는 API입니다.  
    """
)
def update_user(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_user_info(db, current_user, data)