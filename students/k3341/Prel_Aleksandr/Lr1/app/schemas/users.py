from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.time import MoscowDatetime


class BookInUser(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class LibraryItemInUser(BaseModel):
    id: int
    book_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    book: Optional[BookInUser] = None

    class Config:
        from_attributes = True


class ExchangeRequestInUser(BaseModel):
    id: int
    requested_item_id: int
    status: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия, необязательное поле")
    email: str
    password: str
    city: Optional[str] = None
    contact_info: Optional[str] = None


class UserRead(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = Field(default=None, description="Фамилия")
    email: str
    city: Optional[str] = None
    contact_info: Optional[str] = None
    bio: Optional[str] = None
    created_at: MoscowDatetime
    created_books: List[BookInUser] = Field(default_factory=list)
    library_items: List[LibraryItemInUser] = Field(default_factory=list)
    exchange_requests_sent: List[ExchangeRequestInUser] = Field(default_factory=list)

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия. Не передавать для сохранения текущей; null очищает поле")
    email: Optional[str] = None
    city: Optional[str] = None
    contact_info: Optional[str] = None
    bio: Optional[str] = None
