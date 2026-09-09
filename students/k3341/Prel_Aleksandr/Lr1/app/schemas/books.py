from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.time import MoscowDatetime


class UserInBook(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class GenreInBook(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class LibraryItemInBook(BaseModel):
    id: int
    user_id: int
    condition: str
    status: str
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None


class BookRead(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None
    created_by_id: int
    created_at: MoscowDatetime
    created_by: Optional[UserInBook] = None
    genres: List[GenreInBook] = Field(default_factory=list)
    library_items: List[LibraryItemInBook] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
