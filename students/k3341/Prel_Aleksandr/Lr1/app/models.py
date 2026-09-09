from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utc_now


class BookCondition(str, Enum):
    new = "new"
    good = "good"
    worn = "worn"
    damaged = "damaged"


class LibraryItemStatus(str, Enum):
    available = "available"
    reserved = "reserved"
    exchanged = "exchanged"


class ExchangeRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"


# Промежуточная таблица: одна книга может иметь несколько жанров и наоборот.
class BookGenreLink(SQLModel, table=True):
    __tablename__ = "book_genre_links"

    # Два поля образуют общий первичный ключ: пара книга-жанр не может повториться.
    book_id: Optional[int] = Field(
        default=None,
        foreign_key="books.id",
        primary_key=True,
    )
    genre_id: Optional[int] = Field(
        default=None,
        foreign_key="genres.id",
        primary_key=True,
    )


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    last_name: Optional[str] = Field(default=None, max_length=100)
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    city: Optional[str] = None
    contact_info: Optional[str] = None
    bio: Optional[str] = ""
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), nullable=False)

    # Relationship даёт доступ к связанным объектам; отдельного столбца-списка в БД нет.
    # back_populates указывает обратное свойство у связанной модели.
    created_books: List["Book"] = Relationship(back_populates="created_by")
    library_items: List["LibraryItem"] = Relationship(back_populates="user")
    exchange_requests_sent: List["ExchangeRequest"] = Relationship(back_populates="requester")


class Genre(SQLModel, table=True):
    __tablename__ = "genres"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    description: Optional[str] = ""

    books: List["Book"] = Relationship(
        back_populates="genres",
        link_model=BookGenreLink,
    )


# Общая карточка произведения; состояние конкретной копии хранится в LibraryItem.
class Book(SQLModel, table=True):
    __tablename__ = "books"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    isbn: Optional[str] = Field(default=None, sa_column=Column(String, unique=True, index=True))
    description: Optional[str] = ""
    # Это создатель общей карточки, а не обязательно владелец физической книги.
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), nullable=False)

    created_by: Optional[User] = Relationship(back_populates="created_books")
    genres: List[Genre] = Relationship(
        back_populates="books",
        link_model=BookGenreLink,
    )
    library_items: List["LibraryItem"] = Relationship(back_populates="book")


# Физический экземпляр связывает книгу с владельцем и хранит состояние этой связи.
class LibraryItem(SQLModel, table=True):
    __tablename__ = "library_items"

    # Собственный ID позволяет одному владельцу иметь несколько копий одной книги.
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    book_id: int = Field(foreign_key="books.id")
    condition: BookCondition = BookCondition.good
    status: LibraryItemStatus = LibraryItemStatus.available
    comment: Optional[str] = ""
    added_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), nullable=False)

    user: Optional[User] = Relationship(back_populates="library_items")
    book: Optional[Book] = Relationship(back_populates="library_items")
    exchange_requests: List["ExchangeRequest"] = Relationship(back_populates="requested_item")


# Заявка относится к конкретному экземпляру, а не ко всем копиям одной книги.
class ExchangeRequest(SQLModel, table=True):
    __tablename__ = "exchange_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id")
    requested_item_id: int = Field(foreign_key="library_items.id")
    message: Optional[str] = ""
    status: ExchangeRequestStatus = ExchangeRequestStatus.pending
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), nullable=False)
    # До решения по заявке даты нет; принятие, отказ и отмена заполняют её в сервисе.
    resolved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    requester: Optional[User] = Relationship(back_populates="exchange_requests_sent")
    requested_item: Optional[LibraryItem] = Relationship(back_populates="exchange_requests")


class ParsedPage(SQLModel, table=True):
    __tablename__ = "parsed_pages"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    title: str
    source_host: str
    book_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("books.id", ondelete="SET NULL")))
    fetched_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), nullable=False)
