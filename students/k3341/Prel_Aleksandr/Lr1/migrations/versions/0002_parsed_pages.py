"""Track parser source pages without changing existing book records."""

from alembic import op
import sqlalchemy as sa

revision = "0002_parsed_pages"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parsed_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_host", sa.String(), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_parsed_pages_url", "parsed_pages", ["url"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_parsed_pages_url", table_name="parsed_pages")
    op.drop_table("parsed_pages")
