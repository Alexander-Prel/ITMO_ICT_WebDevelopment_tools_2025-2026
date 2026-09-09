from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import User
from app.schemas.users import UserUpdate


class UserService:
    @staticmethod
    def get_all(session: Session) -> list[User]:
        return list(session.exec(select(User)).all())

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> User:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def update(session: Session, user: User, data: UserUpdate) -> User:
        # Свой текущий email можно оставить; конфликт ищем только при выборе другого адреса.
        if data.email and data.email != user.email:
            existing_user = session.exec(select(User).where(User.email == data.email)).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists",
                )
            user.email = data.email

        if data.name:
            user.name = data.name
        # Не передали фамилию: сохраняем прежнюю. Передали null или пробелы: очищаем её.
        if "last_name" in data.model_fields_set:
            user.last_name = (data.last_name.strip() or None) if data.last_name is not None else None
        # None означает, что это поле не обновляем; пустая строка позволяет очистить текст.
        if data.bio is not None:
            user.bio = data.bio
        if data.city is not None:
            user.city = data.city
        if data.contact_info is not None:
            user.contact_info = data.contact_info

        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def delete(session: Session, user: User) -> dict:
        # Профиль нужен связанным книгам и заявкам: не удаляем вместе с ним чужую историю.
        if user.created_books or user.library_items or user.exchange_requests_sent:
            raise HTTPException(status_code=409, detail="User has related books, library items or exchange requests")
        session.delete(user)
        session.commit()
        return {"message": "User deleted successfully"}
