from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from app.config.config import settings
from app.config.errors import ErrorMessages
from app.config.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, UserUpdate
from app.db.user_db import get_user_by_email, create_user, get_user_by_id
from app.db.company_db import get_company_by_id


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

# 회원가입
def signup_user(db: Session, data: UserCreate):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.EMAIL_ALREADY_EXISTS)

    company = get_company_by_id(db, data.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.INVALID_COMPANY_ID)
    
    if data.password != data.password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.PASSWORD_MISMATCH)

    return create_user(db, data)


# 로그인
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def login_user(db: Session, data: UserLogin):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# 현재 사용자 가져오기
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ErrorMessages.INVALID_AUTHENTICATION,
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception
    return user

def get_my_info(current_user: User) -> UserResponse:
    return UserResponse.model_validate(current_user)


# 회원 정보 수정
def update_user_info(
    db: Session,
    current_user: User,
    data: UserUpdate
) -> UserResponse:
    if data.email and data.email != current_user.email:
        if get_user_by_email(db, data.email):
            raise HTTPException(status_code=400, detail=ErrorMessages.EMAIL_ALREADY_EXISTS)
        current_user.email = data.email

    if data.password:
        if data.password != data.password_confirm:
            raise HTTPException(status_code=400, detail=ErrorMessages.PASSWORD_MISMATCH)
        current_user.hashed_password = pwd_context.hash(data.password)

    if data.company_id and data.company_id != current_user.company_id:
        if not get_company_by_id(db, data.company_id):
            raise HTTPException(status_code=400, detail=ErrorMessages.INVALID_COMPANY_ID)
        current_user.company_id = data.company_id

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
