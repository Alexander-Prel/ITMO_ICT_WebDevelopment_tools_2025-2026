from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.models import Book, BookCondition, ExchangeRequestStatus, LibraryItem, LibraryItemStatus, User
from app.schemas.library_items import LibraryItemCreate, LibraryItemUpdate
from app.services.enums import parse_enum
from app.services.permissions import ensure_library_item_owner, get_book_or_404, get_library_item_or_404


class LibraryItemService:
    @staticmethod
    def create(session: Session, data: LibraryItemCreate, user: User) -> LibraryItem:
        get_book_or_404(session, data.book_id)
        # Карточка книги уже существует; создаём её экземпляр у пользователя из токена.
        item = LibraryItem(
            user_id=user.id,
            book_id=data.book_id,
            condition=parse_enum(BookCondition, data.condition, "condition"),
            status=LibraryItemStatus.available,
            comment=data.comment,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def get_all(session: Session) -> list[LibraryItem]:
        return list(session.exec(select(LibraryItem)).all())

    @staticmethod
    def search(session: Session, user: User, q: str | None, city: str | None,
               available_only: bool, limit: int, offset: int) -> list[LibraryItem]:
        # Случайный пробел при вводе не должен мешать поиску.
        q = q.strip() if q else None
        city = city.strip() if city else None
        # Название берём из карточки книги, город из профиля владельца экземпляра.
        statement = select(LibraryItem).join(Book).join(User, LibraryItem.user_id == User.id)
        # Даже при available_only=False собственные экземпляры не входят в поиск чужих книг.
        statement = statement.where(LibraryItem.user_id != user.id)
        if q:
            statement = statement.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
        if city:
            statement = statement.where(User.city.ilike(f"%{city}%"))
        if available_only:
            statement = statement.where(LibraryItem.status == LibraryItemStatus.available)
        return list(session.exec(statement.order_by(LibraryItem.id).offset(offset).limit(limit)).all())

    @staticmethod
    def get_my_library(session: Session, user: User) -> list[LibraryItem]:
        return list(session.exec(select(LibraryItem).where(LibraryItem.user_id == user.id)).all())

    @staticmethod
    def get_by_id(session: Session, item_id: int) -> LibraryItem:
        return get_library_item_or_404(session, item_id)

    @staticmethod
    def update(session: Session, item_id: int, data: LibraryItemUpdate, user: User) -> LibraryItem:
        item = get_library_item_or_404(session, item_id, lock=True)
        ensure_library_item_owner(item, user)

        if data.condition is not None:
            item.condition = parse_enum(BookCondition, data.condition, "condition")
        if data.status is not None:
            new_status = parse_enum(LibraryItemStatus, data.status, "status")
            # Нельзя снова предлагать копию, на которую уже приняли заявку другого читателя.
            if new_status == LibraryItemStatus.available and any(
                request.status == ExchangeRequestStatus.accepted for request in item.exchange_requests
            ):
                raise HTTPException(status_code=409, detail="A copy with an accepted exchange cannot be offered again")
            item.status = new_status
        if data.comment is not None:
            item.comment = data.comment

        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def delete(session: Session, item_id: int, user: User) -> dict:
        item = get_library_item_or_404(session, item_id)
        ensure_library_item_owner(item, user)
        # Сохраняем экземпляр, на который ссылается история заявок, даже завершённых.
        if item.exchange_requests:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Library item cannot be deleted while it has exchange requests",
            )

        session.delete(item)
        session.commit()
        return {"message": "Library item deleted successfully"}
