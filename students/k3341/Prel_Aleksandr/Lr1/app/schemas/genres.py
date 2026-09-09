from typing import List, Optional

from pydantic import BaseModel, Field


class BookInGenre(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class GenreCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GenreRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    books: List[BookInGenre] = Field(default_factory=list)

    class Config:
        from_attributes = True


class GenreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
