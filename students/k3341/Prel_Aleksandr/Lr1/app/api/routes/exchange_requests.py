from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import ExchangeRequest, User
from app.schemas.exchange_requests import ExchangeRequestCreate, ExchangeRequestRead
from app.services.deps import get_current_user
from app.services.exchange_request_service import ExchangeRequestService


router = APIRouter(prefix="/exchange-requests", tags=["Exchange Requests"])


@router.post("/", response_model=ExchangeRequestRead)
def create_exchange_request(
    data: ExchangeRequestCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.create(session, data, current_user)


@router.get("/", response_model=List[ExchangeRequestRead])
def get_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_all(session, current_user)


@router.get("/me", response_model=List[ExchangeRequestRead])
def get_my_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_my_requests(session, current_user)


@router.get("/incoming", response_model=List[ExchangeRequestRead])
def get_incoming_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_incoming_requests(session, current_user)


@router.get("/{request_id}", response_model=ExchangeRequestRead)
def get_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.get_by_id(session, request_id, current_user)


@router.patch("/{request_id}/accept", response_model=ExchangeRequestRead)
def accept_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.accept(session, request_id, current_user)


@router.patch("/{request_id}/decline", response_model=ExchangeRequestRead)
def decline_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.decline(session, request_id, current_user)


@router.patch("/{request_id}/cancel", response_model=ExchangeRequestRead)
def cancel_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.cancel(session, request_id, current_user)
