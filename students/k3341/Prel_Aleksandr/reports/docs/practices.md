# Практики 1.1-1.3

Каждая практика представлена отдельной папкой и точкой входа.

| Практика | Реализация | Исходники |
| --- | --- | --- |
| 1.1 | FastAPI, Pydantic, хранение в памяти, CRUD книг и авторов, вложенные ответы | [practice_1_1](https://github.com/Alexander-Prel/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/Prel_Aleksandr-Lr1/students/k3341/Prel_Aleksandr/Lr1/practices/practice_1_1) |
| 1.2 | PostgreSQL, SQLModel, связи и `create_all` в схеме `practice_1_2` | [practice_1_2](https://github.com/Alexander-Prel/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/Prel_Aleksandr-Lr1/students/k3341/Prel_Aleksandr/Lr1/practices/practice_1_2) |
| 1.3 | Alembic, переменные окружения, разделение кода, схема `practice_1_3` | [practice_1_3](https://github.com/Alexander-Prel/ITMO_ICT_WebDevelopment_tools_2025-2026/tree/Prel_Aleksandr-Lr1/students/k3341/Prel_Aleksandr/Lr1/practices/practice_1_3) |

Практики 1.2 и 1.3 не дублируют итоговое приложение. Общая фабрика
`practices/database_app.py` подключает его модели, роутеры и сервисы,
меняя способ подготовки схемы БД. В 1.2 таблицы создаёт SQLModel,
в 1.3 на выделенном соединении применяются миграции Alembic.
Данные двух практик не смешиваются с основной схемой `public`.

В 1.1 отдельная упрощённая модель: автор является вложенным объектом,
жанры возвращаются списком. В итоговом приложении автор книги хранится
строкой; связи описывают владельцев, экземпляры и жанры.

Код всех практик приведён в [приложении к отчёту](practice_source.md).
Команды запуска и требования к окружению приведены в [инструкции](setup.md).
