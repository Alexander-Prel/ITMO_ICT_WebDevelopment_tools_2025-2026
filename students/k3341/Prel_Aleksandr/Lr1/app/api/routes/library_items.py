from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models import LibraryItem, User
from app.schemas.auth import MessageResponse
from app.schemas.library_items import LibraryItemCreate, LibraryItemRead, LibraryItemUpdate
from app.services.deps import get_current_user
from app.services.library_item_service import LibraryItemService


router = APIRouter(prefix="/library-items", tags=["Library Items"])


@router.post("/", response_model=LibraryItemRead)
def add_book_to_library(
    data: LibraryItemCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> LibraryItem:
    return LibraryItemService.create(session, data, current_user)


@router.get("/", response_model=List[LibraryItemRead])
def get_library_items(session: Session = Depends(get_session)) -> list[LibraryItem]:
    return LibraryItemService.get_all(session)


@router.get("/me", response_model=List[LibraryItemRead])
def get_my_library(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[LibraryItem]:
    return LibraryItemService.get_my_library(session, current_user)


@router.get("/search", response_model=List[LibraryItemRead])
def search_library_items(
    q: str | None = Query(default=None, description="Поисковая строка: часть названия книги или имени автора. Пробелы по краям игнорируются"),
    city: str | None = Query(default=None, description="Город владельца экземпляра. Пробелы по краям игнорируются"),
    available_only: bool = Query(default=True, description="Показывать только доступные для обмена экземпляры других пользователей"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимальное количество результатов"),
    offset: int = Query(default=0, ge=0, description="Количество результатов, которые нужно пропустить"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[LibraryItem]:
    return LibraryItemService.search(session, current_user, q, city, available_only, limit, offset)


@router.get("/{item_id}", response_model=LibraryItemRead)
def get_library_item(item_id: int, session: Session = Depends(get_session)) -> LibraryItem:
    return LibraryItemService.get_by_id(session, item_id)


@router.patch("/{item_id}", response_model=LibraryItemRead)
def update_library_item(
    item_id: int,
    data: LibraryItemUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> LibraryItem:
    return LibraryItemService.update(session, item_id, data, current_user)


@router.delete("/{item_id}", response_model=MessageResponse)
def delete_library_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return LibraryItemService.delete(session, item_id, current_user)
