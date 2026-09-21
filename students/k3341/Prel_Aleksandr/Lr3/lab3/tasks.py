from lab3.celery_app import celery_app
from lab3.service import parse_and_save


@celery_app.task(name="lab3.parse_page")
def parse_page_task(url: str) -> dict:
    # Не перехватываем исключение: Celery пометит задачу как FAILURE.
    return parse_and_save(url).model_dump(mode="json")
