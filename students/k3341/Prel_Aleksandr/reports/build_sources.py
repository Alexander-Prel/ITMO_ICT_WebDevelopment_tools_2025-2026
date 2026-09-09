"""Build report appendices from an explicit list of public source files."""

from pathlib import Path


REPORTS = Path(__file__).resolve().parent
PROJECT = REPORTS.parent / "Lr1"
DOCS = REPORTS / "docs"
GROUPS = {
    "models.md": ("Модели данных", ["app/models.py", "app/core/time.py"]),
    "database.md": ("Подключение и миграции", [
        "app/core/config.py", "app/db/session.py", "alembic.ini",
        "migrations/env.py", "migrations/versions/*.py",
    ]),
    "api.md": ("Код эндпоинтов", ["app/main.py", "app/api/routes/*.py"]),
    "schemas.md": ("Схемы API", ["app/schemas/*.py"]),
    "services.md": ("Бизнес-логика и авторизация", [
        "app/core/security.py", "app/services/*.py",
    ]),
    "practice_source.md": ("Код практик", [
        "practices/database_app.py", "practices/practice_1_*/*.py",
    ]),
}


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    for target, (title, patterns) in GROUPS.items():
        sections = [f"# {title}\n\nФинальная версия кода. Пути указаны от папки `Lr1`.\n"]
        for pattern in patterns:
            for path in sorted(PROJECT.glob(pattern)):
                if path.name == "__init__.py":
                    continue
                language = "python" if path.suffix == ".py" else "ini"
                sections.append(
                    f"\n## `{path.relative_to(PROJECT)}`\n\n```{language}\n"
                    + path.read_text(encoding="utf-8").rstrip() + "\n```\n"
                )
        (DOCS / target).write_text("".join(sections), encoding="utf-8")
    (DOCS / "setup.md").write_text(
        (PROJECT / "README.md").read_text(encoding="utf-8"), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
