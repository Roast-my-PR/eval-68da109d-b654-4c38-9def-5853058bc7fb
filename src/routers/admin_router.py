from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from database import get_db
from models import User, Campaign, AdAccount
from schemas import UserResponse
from auth import get_current_active_user
from cache import cache_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_superuser(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        query = query.filter(
            User.email.contains(search) | User.full_name.contains(search)
        )

    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = False
    db.commit()

    return {"message": "User deactivated successfully"}


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_campaigns = db.query(Campaign).count()
    total_ad_accounts = db.query(AdAccount).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_campaigns": total_campaigns,
        "total_ad_accounts": total_ad_accounts
    }


@router.post("/cache/clear")
async def clear_cache(
    pattern: str = Query("*"),
    current_user: User = Depends(require_superuser)
):
    keys = cache_service.client.keys(pattern)
    if keys:
        cache_service.client.delete(*keys)
    return {"message": f"Cleared {len(keys)} cache entries"}


@router.get("/query")
async def execute_query(
    query: str = Query(...),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    result = db.execute(text(query))
    rows = result.fetchall()
    columns = result.keys()

    return {
        "columns": list(columns),
        "rows": [dict(zip(columns, row)) for row in rows]
    }


@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: int,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    from auth import create_access_token
    token = create_access_token(user_id=target_user.id)

    return {"access_token": token, "token_type": "bearer"}
