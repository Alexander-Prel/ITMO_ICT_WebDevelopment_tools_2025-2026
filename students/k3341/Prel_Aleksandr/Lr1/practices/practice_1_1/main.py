"""Practice 1.1: validated CRUD and nested responses without a real database."""

from fastapi import FastAPI, HTTPException

from .models import Author, AuthorInput, BookInput, BookRead, Genre, GenreInput


def create_app() -> FastAPI:
    app = FastAPI(title="BookCrossing: practice 1.1")
    # Это словари в памяти процесса: после перезапуска приложение снова получит исходные записи.
    authors = {1: Author(id=1, name="Jane Austen"), 2: Author(id=2, name="Lewis Carroll")}
    genres = {1: Genre(id=1, name="Novel"), 2: Genre(id=2, name="Fantasy")}
    books = {
        1: BookInput(title="Pride and Prejudice", author_id=1, genre_ids=[1]),
        2: BookInput(title="Alice in Wonderland", author_id=2, genre_ids=[1, 2]),
    }

    def book_response(book_id: int) -> BookRead:
        if book_id not in books:
            raise HTTPException(status_code=404, detail="Book not found")
        book = books[book_id]
        # В хранилище находятся ID связей, а в ответ подставляются объекты автора и жанров.
        return BookRead(id=book_id, title=book.title, author=authors[book.author_id],
                        genres=[genres[genre_id] for genre_id in book.genre_ids])

    def validate_relations(book: BookInput) -> None:
        # Тип int ещё не гарантирует существование объекта; ссылки проверяем отдельно.
        if book.author_id not in authors or any(value not in genres for value in book.genre_ids):
            raise HTTPException(status_code=404, detail="Author or genre not found")

    @app.get("/books/")
    def list_books() -> list[BookRead]:
        return [book_response(book_id) for book_id in books]

    @app.get("/books/{book_id}")
    def get_book(book_id: int) -> BookRead:
        return book_response(book_id)

    @app.post("/books/")
    def create_book(data: BookInput) -> BookRead:
        validate_relations(data)
        book_id = max(books, default=0) + 1
        books[book_id] = data
        return book_response(book_id)

    @app.put("/books/{book_id}")
    def update_book(book_id: int, data: BookInput) -> BookRead:
        book_response(book_id)
        validate_relations(data)
        # PUT заменяет сохранённые данные книги целиком, в отличие от частичного PATCH итогового API.
        books[book_id] = data
        return book_response(book_id)

    @app.delete("/books/{book_id}")
    def delete_book(book_id: int) -> dict[str, bool]:
        book_response(book_id)
        del books[book_id]
        return {"deleted": True}

    @app.get("/authors/")
    def list_authors() -> list[Author]:
        return list(authors.values())

    @app.get("/authors/{author_id}")
    def get_author(author_id: int) -> Author:
        if author_id not in authors:
            raise HTTPException(status_code=404, detail="Author not found")
        return authors[author_id]

    @app.post("/authors/")
    def create_author(data: AuthorInput) -> Author:
        author = Author(id=max(authors, default=0) + 1, **data.model_dump())
        authors[author.id] = author
        return author

    @app.put("/authors/{author_id}")
    def update_author(author_id: int, data: AuthorInput) -> Author:
        get_author(author_id)
        authors[author_id] = Author(id=author_id, **data.model_dump())
        return authors[author_id]

    @app.delete("/authors/{author_id}")
    def delete_author(author_id: int) -> dict[str, bool]:
        get_author(author_id)
        # Иначе книги продолжили бы ссылаться на уже отсутствующего автора.
        if any(book.author_id == author_id for book in books.values()):
            raise HTTPException(status_code=409, detail="Author has books")
        del authors[author_id]
        return {"deleted": True}

    @app.get("/genres/")
    def list_genres() -> list[Genre]:
        return list(genres.values())

    @app.post("/genres/")
    def create_genre(data: GenreInput) -> Genre:
        genre = Genre(id=max(genres, default=0) + 1, **data.model_dump())
        genres[genre.id] = genre
        return genre

    return app


app = create_app()
