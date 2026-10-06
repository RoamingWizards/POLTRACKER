"""Sort helpers that make SQLite and PostgreSQL return rows in the same order."""

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session


def text_order(session: Session, column: ColumnElement) -> ColumnElement:
    """Compare text by raw bytes on every database.

    SQLite compares text by bytes. PostgreSQL uses the database collation, which on Linux is
    often a locale (en_US) that ignores case and punctuation, so the same names can sort
    differently. `COLLATE "C"` is byte order on PostgreSQL.
    """
    return column.collate("C") if session.get_bind().dialect.name == "postgresql" else column


def nulls_last(expression: ColumnElement) -> ColumnElement:
    """NULLs sort last whether ascending or descending. SQLite and PostgreSQL otherwise disagree."""
    return expression.nulls_last()
