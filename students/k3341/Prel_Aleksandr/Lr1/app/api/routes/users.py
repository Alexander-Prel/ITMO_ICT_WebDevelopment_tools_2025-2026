from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.users import UserRead, UserUpdate
from app.services.deps import get_current_user
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserRead])
def get_users(session: Session = Depends(get_session)) -> list[User]:
    return UserService.get_all(session)


# Фиксированный /me объявлен раньше /{user_id}, иначе слово me может попасть в параметр ID.
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    return UserService.update(session, current_user, data)


@router.delete("/me", response_model=MessageResponse)
def delete_me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return UserService.delete(session, current_user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    return UserService.get_by_id(session, user_id)
