from typing import Optional

from pydantic import BaseModel

from app.schemas.time import MoscowDatetime


class UserInLibraryItem(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class BookInLibraryItem(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


# Владельца берём из JWT, начальный статус задаёт сервис; клиент выбирает только книгу и её состояние.
class LibraryItemCreate(BaseModel):
    book_id: int
    condition: str = "good"
    comment: Optional[str] = None


class LibraryItemRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    added_at: MoscowDatetime
    user: Optional[UserInLibraryItem] = None
    book: Optional[BookInLibraryItem] = None

    class Config:
        from_attributes = True


class LibraryItemUpdate(BaseModel):
    condition: Optional[str] = None
    status: Optional[str] = None
    comment: Optional[str] = None
