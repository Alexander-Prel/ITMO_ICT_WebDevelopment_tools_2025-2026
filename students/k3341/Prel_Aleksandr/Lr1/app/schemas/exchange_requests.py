from typing import Optional

from pydantic import BaseModel

from app.schemas.time import MoscowDatetime


class UserInExchangeRequest(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class BookInExchangeRequest(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class LibraryItemInExchangeRequest(BaseModel):
    id: int
    user_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    book: Optional[BookInExchangeRequest] = None
    user: Optional[UserInExchangeRequest] = None

    class Config:
        from_attributes = True


# Запрашивается ID экземпляра, а не ID общей карточки книги.
class ExchangeRequestCreate(BaseModel):
    requested_item_id: int
    message: Optional[str] = None


class ExchangeRequestRead(BaseModel):
    id: int
    requester_id: int
    requested_item_id: int
    message: Optional[str] = None
    status: str
    created_at: MoscowDatetime
    resolved_at: Optional[MoscowDatetime] = None
    requester: Optional[UserInExchangeRequest] = None
    requested_item: Optional[LibraryItemInExchangeRequest] = None

    class Config:
        from_attributes = True
