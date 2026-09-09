from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models import Book, User
from app.schemas.auth import MessageResponse
from app.schemas.books import BookCreate, BookRead, BookUpdate
from app.services.book_service import BookService
from app.services.deps import get_current_user


router = APIRouter(prefix="/books", tags=["Books"])


# BookCreate проверяет входной JSON, Depends даёт пользователя и сессию, BookRead описывает ответ.
@router.post("/", response_model=BookRead)
def create_book(
    data: BookCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    # Роутер передаёт запрос сервису; правила создания книги находятся в BookService.
    return BookService.create(session, data, current_user)


@router.get("/", response_model=List[BookRead])
def get_books(
    q: str | None = Query(default=None, description="Поисковая строка: часть названия книги или имени автора. Пробелы по краям игнорируются"),
    session: Session = Depends(get_session),
) -> list[Book]:
    return BookService.get_all(session, q=q)


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, session: Session = Depends(get_session)) -> Book:
    return BookService.get_by_id(session, book_id)


@router.patch("/{book_id}", response_model=BookRead)
def update_book(
    book_id: int,
    data: BookUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.update(session, book_id, data, current_user)


@router.delete("/{book_id}", response_model=MessageResponse)
def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return BookService.delete(session, book_id, current_user)


@router.post("/{book_id}/genres/{genre_id}", response_model=BookRead)
def add_genre_to_book(
    book_id: int,
    genre_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.add_genre(session, book_id, genre_id, current_user)


@router.delete("/{book_id}/genres/{genre_id}", response_model=BookRead)
def remove_genre_from_book(
    book_id: int,
    genre_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.remove_genre(session, book_id, genre_id, current_user)
