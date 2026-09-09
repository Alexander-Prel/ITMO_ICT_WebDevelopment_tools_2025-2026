from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest


class AuthService:
    @staticmethod
    def register(session: Session, data: RegisterRequest) -> dict:
        # Email используется для входа, поэтому два аккаунта с ним создать нельзя.
        existing_user = session.exec(select(User).where(User.email == data.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        # В базу передаём только хэш пароля; исходный пароль не сохраняется.
        user = User(
            name=data.name,
            last_name=(data.last_name.strip() or None) if data.last_name is not None else None,
            email=data.email,
            city=data.city,
            contact_info=data.contact_info,
            hashed_password=hash_password(data.password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # sub содержит ID пользователя, чтобы по токену определить автора следующих запросов.
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    def login(session: Session, data: LoginRequest) -> dict:
        user = session.exec(select(User).where(User.email == data.email)).first()
        # Одинаковая ошибка для неверного email и пароля не подсказывает, существует ли аккаунт.
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    def change_password(session: Session, user: User, data: ChangePasswordRequest) -> dict:
        # Одного токена недостаточно: для смены пароля нужно подтвердить старый пароль.
        if not verify_password(data.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is incorrect",
            )

        user.hashed_password = hash_password(data.new_password)
        session.add(user)
        # Уже выданные JWT эта операция не отзывает; они действуют до своего срока окончания.
        session.commit()
        return {"message": "Password changed successfully"}
