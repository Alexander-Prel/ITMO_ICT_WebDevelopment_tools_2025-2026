from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import Genre
from app.schemas.auth import MessageResponse
from app.schemas.genres import GenreCreate, GenreRead, GenreUpdate
from app.services.genre_service import GenreService


router = APIRouter(prefix="/genres", tags=["Genres"])


@router.post("/", response_model=GenreRead)
def create_genre(data: GenreCreate, session: Session = Depends(get_session)) -> Genre:
    return GenreService.create(session, data)


@router.get("/", response_model=List[GenreRead])
def get_genres(session: Session = Depends(get_session)) -> list[Genre]:
    return GenreService.get_all(session)


@router.get("/{genre_id}", response_model=GenreRead)
def get_genre(genre_id: int, session: Session = Depends(get_session)) -> Genre:
    return GenreService.get_by_id(session, genre_id)


@router.patch("/{genre_id}", response_model=GenreRead)
def update_genre(genre_id: int, data: GenreUpdate, session: Session = Depends(get_session)) -> Genre:
    return GenreService.update(session, genre_id, data)


@router.delete("/{genre_id}", response_model=MessageResponse)
def delete_genre(genre_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    return GenreService.delete(session, genre_id)
