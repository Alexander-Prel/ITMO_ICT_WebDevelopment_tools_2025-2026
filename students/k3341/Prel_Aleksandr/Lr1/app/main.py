from fastapi import FastAPI

from app.api.routes import auth, books, exchange_requests, genres, library_items, users
from app.core.config import settings


app = FastAPI(title=settings.app_name)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "BookCrossing API is running"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(genres.router)
app.include_router(books.router)
app.include_router(library_items.router)
app.include_router(exchange_requests.router)
