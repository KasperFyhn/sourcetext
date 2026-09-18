from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Double, ForeignKey, Integer, Sequence, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    labels: Mapped[list["Label"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    scores: Mapped[list["Score"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    groups: Mapped[list["Group"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    spans: Mapped[list["Span"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    temporal_years: Mapped[list["TemporalYear"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    temporal_dates: Mapped[list["TemporalDate"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    temporal_datetimes: Mapped[list["TemporalDatetime"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    free_texts: Mapped[list["FreeText"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    points_2d: Mapped[list["Point2D"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class _ScalarField(Base):
    """Shared shape for the `(id, field_name, value)` tables."""

    __abstract__ = True

    # DuckDB has no native autoincrement (no SERIAL/IDENTITY); a per-table
    # Sequence gives it an explicit `nextval(...)` default to autoincrement from.
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(Integer, Sequence(f"{cls.__tablename__}_id_seq"), primary_key=True)

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False, index=True)


class Label(_ScalarField):
    """Every LabelType field, including the `predictions` and `gold` presets."""

    __tablename__ = "labels"

    value: Mapped[str] = mapped_column(String, nullable=False)

    document: Mapped[Document] = relationship(back_populates="labels")


class Score(_ScalarField):
    """ScoreType fields, e.g. `confidence`."""

    __tablename__ = "scores"

    value: Mapped[float] = mapped_column(Double, nullable=False)

    document: Mapped[Document] = relationship(back_populates="scores")


class Group(_ScalarField):
    """GroupType fields. `value` is a group id, stored as text so it lines up
    with GroupDefinition.group_id."""

    __tablename__ = "groups"

    value: Mapped[str] = mapped_column(String, nullable=False)

    document: Mapped[Document] = relationship(back_populates="groups")


class GroupDefinition(Base):
    """GroupDefinition rows, keyed by which GroupType field they belong to
    so two different GroupType fields can each carry their own definitions.

    `definition` is JSON, not plain text: it may be a bare string, or a richer
    object (e.g. keywords + scores) for the UI to render — not meant to be
    searched at the DB level, just fetched and displayed."""

    __tablename__ = "group_definitions"

    field_name: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str] = mapped_column(String, primary_key=True)
    definition: Mapped[Any] = mapped_column(JSON, nullable=False)


class Span(Base):
    """SpanType rows: one row per span. An document with zero spans simply
    contributes no rows; `score` is optional per span."""

    __tablename__ = "spans"

    span_id: Mapped[int] = mapped_column(Integer, Sequence("spans_span_id_seq"), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    span_start: Mapped[int] = mapped_column(Integer, nullable=False)
    span_end: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Double, nullable=True)

    document: Mapped[Document] = relationship(back_populates="spans")


class TemporalYear(_ScalarField):
    """Temporal fields whose underlying Python value is a bare int (year-level)."""

    __tablename__ = "temporal_year"

    value: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[Document] = relationship(back_populates="temporal_years")


class TemporalDate(_ScalarField):
    """Temporal fields whose underlying Python value is a datetime.date."""

    __tablename__ = "temporal_date"

    value: Mapped[dt.date] = mapped_column(Date, nullable=False)

    document: Mapped[Document] = relationship(back_populates="temporal_dates")


class TemporalDatetime(_ScalarField):
    """Temporal fields whose underlying Python value is a datetime.datetime."""

    __tablename__ = "temporal_datetime"

    value: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)

    document: Mapped[Document] = relationship(back_populates="temporal_datetimes")


class FreeText(_ScalarField):
    """TextType fields, e.g. an editorial-note column."""

    __tablename__ = "free_text"

    value: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped[Document] = relationship(back_populates="free_texts")


class Point2D(Base):
    """Point2DType fields: a 2D point per document (e.g. a projected embedding),
    stored as (x, y) coordinates for a scatter-plot layout."""

    __tablename__ = "points_2d"

    id: Mapped[int] = mapped_column(Integer, Sequence("points_2d_id_seq"), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    x: Mapped[float] = mapped_column(Double, nullable=False)
    y: Mapped[float] = mapped_column(Double, nullable=False)

    document: Mapped[Document] = relationship(back_populates="points_2d")
