from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Genre
from app.schemas.genres import GenreCreate, GenreUpdate


class GenreService:
    @staticmethod
    def create(session: Session, data: GenreCreate) -> Genre:
        existing_genre = session.exec(select(Genre).where(Genre.name == data.name)).first()
        if existing_genre:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Genre with this name already exists",
            )

        genre = Genre(name=data.name, description=data.description)
        session.add(genre)
        session.commit()
        session.refresh(genre)
        return genre

    @staticmethod
    def get_all(session: Session) -> list[Genre]:
        return list(session.exec(select(Genre)).all())

    @staticmethod
    def get_by_id(session: Session, genre_id: int) -> Genre:
        genre = session.get(Genre, genre_id)
        if not genre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found")
        return genre

    @staticmethod
    def update(session: Session, genre_id: int, data: GenreUpdate) -> Genre:
        genre = GenreService.get_by_id(session, genre_id)
        if data.name and data.name != genre.name:
            existing_genre = session.exec(select(Genre).where(Genre.name == data.name)).first()
            if existing_genre:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Genre with this name already exists",
                )
            genre.name = data.name
        if data.description is not None:
            genre.description = data.description

        session.add(genre)
        session.commit()
        session.refresh(genre)
        return genre

    @staticmethod
    def delete(session: Session, genre_id: int) -> dict:
        genre = GenreService.get_by_id(session, genre_id)
        session.delete(genre)
        session.commit()
        return {"message": "Genre deleted successfully"}
