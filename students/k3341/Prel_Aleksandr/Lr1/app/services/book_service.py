from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.models import Book, Genre, User
from app.schemas.books import BookCreate, BookUpdate
from app.services.permissions import ensure_book_creator, get_book_or_404


class BookService:
    @staticmethod
    def create(session: Session, data: BookCreate, user: User) -> Book:
        # Если ISBN указан, он должен быть уникальным; отсутствие ISBN допускается.
        if data.isbn:
            existing_book = session.exec(select(Book).where(Book.isbn == data.isbn)).first()
            if existing_book:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Book with this ISBN already exists",
                )

        book = Book(
            title=data.title,
            author=data.author,
            isbn=data.isbn,
            description=data.description,
            created_by_id=user.id,
        )
        # add готовит запись, commit сохраняет её, refresh получает из БД ID и остальные поля.
        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def get_all(session: Session, q: str | None = None) -> list[Book]:
        q = q.strip() if q else None
        statement = select(Book).order_by(Book.id)
        if q:
            statement = statement.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
        return list(session.exec(statement).all())

    @staticmethod
    def get_by_id(session: Session, book_id: int) -> Book:
        return get_book_or_404(session, book_id)

    @staticmethod
    def update(session: Session, book_id: int, data: BookUpdate, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)

        if data.isbn and data.isbn != book.isbn:
            existing_book = session.exec(select(Book).where(Book.isbn == data.isbn)).first()
            if existing_book:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Book with this ISBN already exists",
                )
            book.isbn = data.isbn

        if data.title:
            book.title = data.title
        if data.author:
            book.author = data.author
        if data.description is not None:
            book.description = data.description

        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def remove_genre(session: Session, book_id: int, genre_id: int, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)
        genre = session.get(Genre, genre_id)
        if genre is None or genre not in book.genres:
            raise HTTPException(status_code=404, detail="Book genre link not found")
        # Удаляем только связь с жанром, а не сам жанр и не книгу.
        book.genres.remove(genre)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def delete(session: Session, book_id: int, user: User) -> dict:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)
        # Карточка общая: её нельзя удалить, пока на неё ссылаются экземпляры пользователей.
        if book.library_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book cannot be deleted while users have it in libraries",
            )

        session.delete(book)
        session.commit()
        return {"message": "Book deleted successfully"}

    @staticmethod
    def add_genre(session: Session, book_id: int, genre_id: int, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)

        genre = session.get(Genre, genre_id)
        if not genre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found")

        # Повторное добавление того же жанра не создаёт вторую связь.
        if genre not in book.genres:
            book.genres.append(genre)
            session.add(book)
            session.commit()
            session.refresh(book)
        return book
