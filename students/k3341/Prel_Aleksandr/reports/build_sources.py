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
    lab2 = REPORTS.parent / "Lr2"
    sections = ["# Исходный код ЛР2\n\nПути указаны от папки `Lr2`.\n"]
    for pattern in ("lab2/common.py", "lab2/task1/*.py", "lab2/task2/*.py"):
        for path in sorted(lab2.glob(pattern)):
            if path.name == "__init__.py":
                continue
            sections.append(
                f"\n## `{path.relative_to(lab2)}`\n\n```python\n"
                + path.read_text(encoding="utf-8").rstrip() + "\n```\n"
            )
    (DOCS / "lab2_source.md").write_text("".join(sections), encoding="utf-8")
    (DOCS / "lab2_setup.md").write_text(
        (lab2 / "README.md").read_text(encoding="utf-8").replace(
            "(../reports/docs/lab2.md)", "(lab2.md)"
        ), encoding="utf-8"
    )
    lab3 = REPORTS.parent / "Lr3"
    sections = ["# Исходный код ЛР3\n\nПути указаны от папки `Lr3`.\n"]
    for pattern in ("lab3/*.py", "Dockerfile.*", "docker-compose.yml", "*requirements.txt", "*.sh", ".env.example"):
        for path in sorted(lab3.glob(pattern)):
            if path.name == "__init__.py":
                continue
            language = {".py": "python", ".yml": "yaml", ".sh": "bash"}.get(path.suffix, "text")
            sections.append(
                f"\n## `{path.relative_to(lab3)}`\n\n```{language}\n"
                + path.read_text(encoding="utf-8").rstrip() + "\n```\n"
            )
    sections.append("\n## `.dockerignore` в личной папке\n\n```text\n"
                    + (REPORTS.parent / ".dockerignore").read_text(encoding="utf-8").rstrip() + "\n```\n")
    (DOCS / "lab3_source.md").write_text("".join(sections), encoding="utf-8")
    (DOCS / "lab3_setup.md").write_text(
        (lab3 / "README.md").read_text(encoding="utf-8").replace(
            "(../reports/docs/lab3.md)", "(lab3.md)"
        ), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
