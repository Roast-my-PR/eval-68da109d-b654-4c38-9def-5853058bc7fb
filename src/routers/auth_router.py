from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from models import User
from schemas import UserCreate, UserResponse, Token
from auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    generate_api_key
)
from config import get_settings
from cache import cache_service

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(
        user_id=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/api-key")
async def generate_user_api_key(
    current_user: User = Depends(get_current_active_user)
):
    api_key = generate_api_key(current_user.id)
    return {"api_key": api_key}


@router.post("/password-reset")
async def request_password_reset(
    email: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    reset_token = generate_api_key(user.id if user else 0)

    if user:
        cache_service.set(f"reset:{reset_token}", user.id, ttl=3600)

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/{token}")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    user_id = cache_service.get(f"reset:{token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.hashed_password = get_password_hash(new_password)
    db.commit()

    cache_service.delete(f"reset:{token}")

    return {"message": "Password reset successful"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    return {"message": "Successfully logged out"}
