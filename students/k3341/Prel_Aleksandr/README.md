# Прель Александр, K3341

Курс: Web Development Tools, 2025-2026.

- [Лабораторная работа 1: буккросинг](Lr1/README.md).
- [Лабораторная работа 2: потоки, процессы, асинхронность](Lr2/README.md).
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
Статический сайт создаётся в `reports/site/`; исходники приложения находятся в `Lr1/`,
суммирование и парсеры в `Lr2/`. ЛР2 использует модели и БД из ЛР1.

ЛР2 содержит код и результаты двух задач: замеры парсинга и завершённый
21 сентября CPU-эксперимент на `1..10^10` вместо `1..10^13`. Согласование уменьшения
преподавателем не подтверждено. ЛР1 сдаётся отдельно в
[PR #169](https://github.com/TonikX/ITMO_ICT_WebDevelopment_tools_2025-2026/pull/169).
