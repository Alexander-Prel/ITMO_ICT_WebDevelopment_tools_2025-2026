from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from kombu.exceptions import OperationalError
from pydantic import BaseModel, ConfigDict
from redis.exceptions import RedisError
from sqlmodel import Session, select

from app.db.session import get_session
from app.main import app
from app.models import ParsedPage, User
from app.schemas.time import MoscowDatetime
from app.services.deps import get_current_user
from lab3.celery_app import celery_app, register_task, task_exists, unregister_task
from lab3.schemas import ParseRequest, ParseResult, TaskAccepted, TaskStatus
from lab3.service import ParseServiceError, parse_and_save
from lab3.tasks import parse_page_task


router = APIRouter(prefix="/parser", tags=["Parser — LR3"])


class ParsedPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    source_host: str
    book_id: int | None
    fetched_at: MoscowDatetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/parse", response_model=ParseResult)
def parse_sync(data: ParseRequest, current_user: User = Depends(get_current_user)) -> ParseResult:
    try:
        return parse_and_save(data.url)
    except ParseServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail="Could not save the parsed page") from error


@router.post("/parse/async", response_model=TaskAccepted, status_code=202)
def parse_async(data: ParseRequest, current_user: User = Depends(get_current_user)) -> TaskAccepted:
    task_id = str(uuid4())
    try:
        register_task(task_id)
        parse_page_task.apply_async(args=[data.url], task_id=task_id, retry=False)
    except (RedisError, OperationalError, OSError) as error:
        try:
            unregister_task(task_id)
        except (RedisError, OSError):
            pass
        raise HTTPException(status_code=503, detail="Task queue is unavailable") from error
    return TaskAccepted(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: UUID, current_user: User = Depends(get_current_user)) -> TaskStatus:
    task_id = str(task_id)
    try:
        if not task_exists(task_id):
            raise HTTPException(status_code=404, detail="Task not found or expired")
        result = celery_app.AsyncResult(task_id)
        status = result.state
        if status == "SUCCESS":
            return TaskStatus(task_id=task_id, status=status, result=result.result)
        if status == "FAILURE":
            return TaskStatus(task_id=task_id, status=status, error=str(result.result))
        return TaskStatus(task_id=task_id, status=status)
    except (RedisError, OperationalError, OSError) as error:
        raise HTTPException(status_code=503, detail="Task status storage is unavailable") from error


@router.get("/pages", response_model=list[ParsedPageRead])
def get_pages(session: Session = Depends(get_session)) -> list[ParsedPage]:
    return list(session.exec(select(ParsedPage).order_by(ParsedPage.id)).all())


app.include_router(router)
