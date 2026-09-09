from pydantic import BaseModel, Field


class AuthorInput(BaseModel):
    name: str = Field(min_length=1)


class Author(AuthorInput):
    id: int


class GenreInput(BaseModel):
    name: str = Field(min_length=1)


class Genre(GenreInput):
    id: int


class BookInput(BaseModel):
    title: str = Field(min_length=1)
    author_id: int
    genre_ids: list[int] = Field(default_factory=list)


class BookRead(BaseModel):
    id: int
    title: str
    author: Author
    genres: list[Genre]
