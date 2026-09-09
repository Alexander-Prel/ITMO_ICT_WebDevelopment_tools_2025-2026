"""Initial bookcrossing schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("contact_info", sa.String(), nullable=True),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_genres_name"), "genres", ["name"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("isbn", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_isbn"), "books", ["isbn"], unique=True)

    op.create_table(
        "book_genre_links",
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("genre_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"]),
        sa.PrimaryKeyConstraint("book_id", "genre_id"),
    )

    op.create_table(
        "library_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "condition",
            sa.Enum("new", "good", "worn", "damaged", name="bookcondition"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("available", "reserved", "exchanged", name="libraryitemstatus"),
            nullable=False,
        ),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "exchange_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("requested_item_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "declined",
                "cancelled",
                name="exchangerequeststatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_item_id"], ["library_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exchange_requests")
    op.drop_table("library_items")
    op.drop_table("book_genre_links")
    op.drop_index(op.f("ix_books_isbn"), table_name="books")
    op.drop_table("books")
    op.drop_index(op.f("ix_genres_name"), table_name="genres")
    op.drop_table("genres")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS exchangerequeststatus")
    op.execute("DROP TYPE IF EXISTS libraryitemstatus")
    op.execute("DROP TYPE IF EXISTS bookcondition")
