from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.database.session import get_db
from app.models.auth import User, UserRole
from app.schemas.auth import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_only = Depends(require_roles(UserRole.ADMIN))

@router.get("", response_model=list[UserRead], dependencies=[admin_only])
def list_users(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.full_name)))

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[admin_only])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email address is already registered")
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}", response_model=UserRead, dependencies=[admin_only])
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit(); db.refresh(user)
    return user
