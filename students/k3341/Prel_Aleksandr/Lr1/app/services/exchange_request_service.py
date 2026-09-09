from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.core.time import utc_now
from app.models import ExchangeRequest, ExchangeRequestStatus, LibraryItem, LibraryItemStatus, User
from app.schemas.exchange_requests import ExchangeRequestCreate
from app.services.permissions import get_library_item_or_404


class ExchangeRequestService:
    @staticmethod
    def create(session: Session, data: ExchangeRequestCreate, user: User) -> ExchangeRequest:
        # Блокировка не даёт одновременно принять обмен и создать заявку на уже занятый экземпляр.
        requested_item = get_library_item_or_404(session, data.requested_item_id, lock=True)

        # Запрашивать можно только чужой экземпляр, который ещё доступен.
        if requested_item.user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User cannot request own book",
            )
        if requested_item.status != LibraryItemStatus.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book is not available for exchange",
            )

        # Пока решение не принято, у одного читателя не должно быть двух заявок на ту же копию.
        existing_request = session.exec(
            select(ExchangeRequest).where(
                ExchangeRequest.requester_id == user.id,
                ExchangeRequest.requested_item_id == requested_item.id,
                ExchangeRequest.status == ExchangeRequestStatus.pending,
            )
        ).first()
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending exchange request already exists",
            )

        # Автор берётся из токена: клиент не может отправить заявку от имени другого человека.
        exchange_request = ExchangeRequest(
            requester_id=user.id,
            requested_item_id=requested_item.id,
            message=data.message,
        )
        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def get_all(session: Session, user: User) -> list[ExchangeRequest]:
        # Показываем только свои исходящие заявки и входящие на свои экземпляры.
        statement = select(ExchangeRequest).join(LibraryItem).where(
            or_(ExchangeRequest.requester_id == user.id, LibraryItem.user_id == user.id)
        )
        return list(session.exec(statement).all())

    @staticmethod
    def get_my_requests(session: Session, user: User) -> list[ExchangeRequest]:
        return list(
            session.exec(
                select(ExchangeRequest).where(ExchangeRequest.requester_id == user.id)
            ).all()
        )

    @staticmethod
    def get_incoming_requests(session: Session, user: User) -> list[ExchangeRequest]:
        return list(
            session.exec(
                select(ExchangeRequest)
                .join(LibraryItem, ExchangeRequest.requested_item_id == LibraryItem.id)
                .where(LibraryItem.user_id == user.id)
            ).all()
        )

    @staticmethod
    def get_by_id(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = session.get(ExchangeRequest, request_id)
        if not exchange_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange request not found",
            )

        # Знать ID недостаточно: читать заявку могут только её автор и владелец экземпляра.
        owner_id = exchange_request.requested_item.user_id
        if exchange_request.requester_id != user.id and owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only requester or book owner can view this exchange request",
            )
        return exchange_request

    @staticmethod
    def accept(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        requested_item = exchange_request.requested_item

        if requested_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only book owner can accept exchange request",
            )
        # По заявке можно принять решение только один раз, пока она ожидает ответа.
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be accepted",
            )

        if requested_item.status != LibraryItemStatus.available:
            raise HTTPException(status_code=400, detail="Book is no longer available")

        # Принятие резервирует копию, но не меняет её владельца и не подтверждает передачу.
        exchange_request.status = ExchangeRequestStatus.accepted
        exchange_request.resolved_at = utc_now()
        requested_item.status = LibraryItemStatus.reserved

        # Один экземпляр нельзя обещать двум людям: остальные ожидающие заявки отклоняем.
        others = session.exec(select(ExchangeRequest).where(
            ExchangeRequest.requested_item_id == requested_item.id,
            ExchangeRequest.id != request_id,
            ExchangeRequest.status == ExchangeRequestStatus.pending,
        )).all()
        for other in others:
            other.status = ExchangeRequestStatus.declined
            other.resolved_at = exchange_request.resolved_at
            session.add(other)

        session.add(requested_item)
        session.add(exchange_request)
        # Решение, резервирование и отклонение остальных заявок сохраняются одной транзакцией.
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def decline(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        requested_item = exchange_request.requested_item

        if requested_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only book owner can decline exchange request",
            )
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be declined",
            )

        # Заявка остаётся в истории. Сам экземпляр здесь не резервируем и не удаляем.
        exchange_request.status = ExchangeRequestStatus.declined
        exchange_request.resolved_at = utc_now()

        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def cancel(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        # Отмена доступна автору заявки, а не владельцу книги; принятую заявку так не отменить.
        if exchange_request.requester_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only requester can cancel exchange request",
            )
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be cancelled",
            )

        exchange_request.status = ExchangeRequestStatus.cancelled
        exchange_request.resolved_at = utc_now()

        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def _get_for_update(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService.get_by_id(session, request_id, user)
        # Заявки на одну копию ждут общую блокировку экземпляра до завершения транзакции.
        get_library_item_or_404(session, exchange_request.requested_item_id, lock=True)
        # Пока мы ждали, другая операция могла изменить заявку: перечитываем её из БД.
        session.refresh(exchange_request)
        return exchange_request
