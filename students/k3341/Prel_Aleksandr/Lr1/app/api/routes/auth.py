from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, MessageResponse, RegisterRequest
from app.services.auth_service import AuthService
from app.services.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


# response_model оставляет только публичные поля, даже если сервис вернул ORM-пользователя с хэшем.
@router.post("/register", response_model=LoginResponse)
def register(data: RegisterRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    return AuthService.register(session, data)


# Вход принимает JSON, а не форму OAuth2: Swagger Authorize используется уже с готовым токеном.
@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    return AuthService.login(session, data)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return AuthService.change_password(session, current_user, data)
