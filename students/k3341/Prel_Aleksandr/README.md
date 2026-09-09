# Прель Александр, K3341

Курс: Web Development Tools, 2025-2026.

- [Лабораторная работа 1: буккросинг](Lr1/README.md).
- [Практика 1.1](Lr1/practices/practice_1_1/README.md).
- [Практика 1.2](Lr1/practices/practice_1_2/README.md).
- [Практика 1.3](Lr1/practices/practice_1_3/README.md).
- [Отчёт на GitHub Pages](https://alexander-prel.github.io/ITMO_ICT_WebDevelopment_tools_2025-2026/).
- [Исходники отчёта MkDocs](reports/).

Сборка документации из этой папки:

```bash
python -m pip install -r reports/requirements.txt
python reports/build_sources.py
python -m mkdocs build --strict -f reports/mkdocs.yml
```

Для локального просмотра: `python -m mkdocs serve -f reports/mkdocs.yml -a 127.0.0.1:8001`.
Статический сайт создаётся в `reports/site/`; исходники приложения находятся в `Lr1/`.
