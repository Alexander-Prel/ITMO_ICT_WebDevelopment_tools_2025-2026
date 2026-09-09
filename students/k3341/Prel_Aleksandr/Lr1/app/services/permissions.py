from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Book, LibraryItem, User


def get_book_or_404(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def get_library_item_or_404(session: Session, item_id: int, *, lock: bool = False) -> LibraryItem:
    if lock:
        # FOR UPDATE удерживает блокировку строки до commit/rollback.
        # populate_existing обновляет объект в сессии, если его уже читали до ожидания.
        item = session.exec(
            select(LibraryItem).where(LibraryItem.id == item_id)
            .with_for_update().execution_options(populate_existing=True)
        ).first()
    else:
        item = session.get(LibraryItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found",
        )
    return item


def ensure_book_creator(book: Book, user: User) -> None:
    # Создатель общей карточки и владелец конкретного экземпляра могут быть разными людьми.
    if book.created_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only book creator can update book metadata",
        )


def ensure_library_item_owner(item: LibraryItem, user: User) -> None:
    if item.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only library item owner can perform this action",
        )
