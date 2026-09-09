"""Add an optional last name without replacing existing users."""

from alembic import op
import sqlalchemy as sa

revision = "0003_user_last_name"
down_revision = "0002_parsed_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_name")
