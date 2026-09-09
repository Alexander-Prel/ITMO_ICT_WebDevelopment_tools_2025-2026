"""Preserve legacy UTC instants while adding explicit time zones."""

from alembic import op
import sqlalchemy as sa

revision = "0004_timezone_aware_dates"
down_revision = "0003_user_last_name"
branch_labels = None
depends_on = None

DATE_COLUMNS = (
    ("users", "created_at", False),
    ("books", "created_at", False),
    ("library_items", "added_at", False),
    ("exchange_requests", "created_at", False),
    ("exchange_requests", "resolved_at", True),
    ("parsed_pages", "fetched_at", False),
)


def upgrade() -> None:
    for table, column, nullable in DATE_COLUMNS:
        # Старые числа означали UTC: добавляем этот пояс явно, не сдвигая сами события.
        op.alter_column(
            table, column,
            existing_type=sa.DateTime(timezone=False),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    # При откате возвращаем прежние UTC-даты без пояса, независимо от настроек подключения.
    for table, column, nullable in reversed(DATE_COLUMNS):
        op.alter_column(
            table, column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
