# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python library for DH/NLP researchers to review model output (classification,
NER, sentiment, clustering, etc.) alongside source text and record interpretive
judgments in situ. See `sourcetext-spec.md` for the full design spec (type
system, internal schema, planned serving layer) and `README.md` for usage
examples — both are kept in sync with the code and are the right place to
check "why" a design choice was made before assuming it's arbitrary.

## Commands

```bash
# Setup (editable install with dev deps: pytest, ruff, pre-commit)
pip install -e ".[dev]"
pre-commit install   # wires ruff into git's pre-commit hook

# Tests
pytest                                  # full suite
pytest tests/test_sourcetext.py         # one file
pytest tests/test_types.py::test_point2d_type_rejects_wrong_length  # one test

# Lint / format (also runs automatically on commit via pre-commit)
ruff check .
ruff check --fix .
ruff format .
pre-commit run --all-files              # run both hooks without committing
```

## Architecture

Every field beyond the raw text is a **typed field** (`LabelType`, `ScoreType`,
`GroupType`, `SpanType`, `TemporalType`, `FreeTextType`, `Point2DType`), and
each one is implemented identically across four files. Understanding one type
end-to-end (e.g. grep for `Point2D`) is the fastest way to understand all of
them:

- **`types.py`** — one `_PrimaryType` subclass per type, validating and
  resolving the raw input (`resolve(data)`). `value_types` (an `isinstance`
  tuple) is the validation contract; types whose shape isn't a flat scalar
  union (`SpanType`, `Point2DType`) still set `value_types` for the outer
  container check but layer custom structural validation on top rather than
  skipping the base check entirely. `definition_types` (currently only set on
  `GroupType`) lets a type accept an optional `definitions=` dict at
  construction — this is a general mechanism on `_PrimaryType`, not a
  `GroupType`-only special case, even though it's the only one wired up today.
- **`schema.py`** — one SQLAlchemy ORM table per type. Most types share the
  `(id, document_id, field_name, value)` shape via the `_ScalarField` mixin;
  `Span` and `GroupDefinition` don't fit that shape and are standalone models.
  `Document` is the root table (`documents.id`, cast to `str` even though IDs
  may be `int`, so one column type covers the union). DuckDB has no
  `SERIAL`/`IDENTITY`, so autoincrement PKs use an explicit `Sequence` per
  table instead of `autoincrement=True`. Numeric columns are `Double`, not
  `Float` — `Float` silently truncates to 32-bit on DuckDB.
- **`db.py`** — the service layer: one `add_*` function per table, each
  taking a `Session` plus parallel `document_ids`/`values` and adding rows
  *without committing* — the caller controls the transaction. Most `add_*`
  functions delegate to the private `_add_scalar_field` helper (mirrors the
  `_ScalarField` mixin: cast, skip `None` values, insert). `get_sessionmaker()`
  builds a `sessionmaker` bound to a DuckDB engine via `duckdb-engine`
  (`Base.metadata.create_all` runs automatically), defaulting to an in-memory
  DB but accepting any SQLAlchemy URL.
- **`sourcetext.py`** — `SourceText.__init__` is the single dispatch point.
  Named presets (`predictions=`, `predictions_confidence=`, `gold_labels=`,
  `scores=`, `groups=`/`group_definitions=`) are wrapped into their typed-field
  instance and merged into the same `fields` dict as arbitrary `**fields`
  entries — from there, one loop resolves each field's values and calls the
  matching `db.add_*` function based on `isinstance` checks. There is
  intentionally **one dispatch path**, not a separate "simple" vs. "expert"
  code path — adding a new preset kwarg means wrapping it before the loop, not
  branching inside it.

**Adding a new primary type** touches all four files plus both docs: a class
in `types.py`, a table in `schema.py`, an `add_*` function in `db.py`, a
dispatch branch in `sourcetext.py`'s loop, an export in `sourcetext/__init__.py`,
and a row/table update in `sourcetext-spec.md` and `README.md`.

**Not yet implemented**: `SourceText.serve()`, the FastAPI serving layer, and
interpretive-annotation write-back are all in `sourcetext-spec.md` as target
design but don't exist in code yet — don't assume they work.
