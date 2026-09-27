# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python library for DH/NLP researchers to review model output (classification,
NER, sentiment, clustering, etc.) alongside source text and record interpretive
judgments in situ. `README.md` is both the landing page (also rendered on PyPI, so
links in it must be absolute GitHub URLs) and the user-facing documentation: its
lower "Documentation" half is the API reference. Keep it in sync with the code,
including its "Project status" list of what isn't built yet.

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

# Package (builds the UI into sourcetext/server/static/, then sdist + wheel into dist/)
./scripts/build.sh
```

**CI / releasing**: `.github/workflows/ci.yml` runs lint (ruff + oxlint/prettier),
pytest on 3.10–3.13, and a full package build (`.github/actions/build-package`) on
pushes/PRs to `main`. To release, bump `version` in `pyproject.toml` and publish a
GitHub release tagged `v<version>`: `publish.yml` reruns CI and uploads the `dist`
artifact from its build job to PyPI via trusted publishing (it fails if the tag and
version disagree). The built UI
is gitignored, so `pyproject.toml` sets hatch `artifacts` at build level (not just on
the wheel target): `python -m build` builds the wheel *from the sdist*, so the sdist
must carry the UI too.

## Architecture

Every field beyond the raw text is a **typed field** (`LabelType`, `ScoreType`,
`GroupType`, `SpanType`, `TemporalType`, `TextType`, `Point2DType`), and
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

**Adding a new primary type** touches all four files plus the README: a class
in `types.py`, a table in `schema.py`, an `add_*` function in `db.py`, a
dispatch branch in `sourcetext.py`'s loop, an export in `sourcetext/__init__.py`,
and a row in the README's "Field types" table.

**Server + UI (scaffold only)**: `SourceText.start_server()` runs the FastAPI app
in `sourcetext/server/` via `BackgroundServer` (blocks in a plain script,
backgrounds when an event loop is already running, e.g. Jupyter). The React/TS
frontend lives in `ui/`; `./scripts/build-frontend.sh` builds it into the
gitignored `sourcetext/server/static/`, which FastAPI mounts at `/` (API routes
live under `/api`; `npm run dev` proxies `/api` to port 8001, or `$SOURCETEXT_API_PORT`). Routes so far:
`GET /api/documents/tabular` (paginated documents + scalar field values + note),
`GET /api/documents/scatter` (unpaginated `point_2d`/`score` fields plotted as
`{documentId, x, y, text, group}` — pass `field=<point_2d field>` to plot one
directly, or `xField=`/`yField=<score fields>` to combine two score fields as axes;
pass neither to just list available fields; optionally add `colorField=<group
field>` to attach that GroupType field's value per point for client-side coloring),
`GET /api/documents/fields` (the full field list, for
a document-detail pane not otherwise loading a page of documents), `GET
/api/documents/{id}` (one document's full scalar field values + note — used to
populate that detail pane on selection from a non-tabular view), and `PUT
/api/documents/{id}/note` (notes live in the `notes` table, which is not a typed
field). Read helpers are in `db/queries.py`. Routes must be `async def`: in-memory
DuckDB is per-thread, so FastAPI's threadpool would see an empty DB. The
`{document_id}`-taking routes are registered after the static `tabular`/`scatter`/
`fields` routes so FastAPI matches those literal paths first.

**Dev workflow**: mock data lives outside the package in `dev/` (one module per
scenario in `dev/scenarios/`, each exposing `make_source_text()`). Run
`./scripts/dev.sh <scenario>` for the API on :8001 plus the hot-reloading Vite
UI on :3000, or `python dev/serve.py <scenario>` alone (serves the built UI from
`sourcetext/server/static/`; startup fails if there is no build). `--dev` sets the
internal `sourcetext.server.app.DEV` switch (not public API), which skips mounting
the built UI (API only); `dev.sh` uses it.

**Not yet implemented**: span rendering and group-definition display in the UI,
and sidecar-file persistence of notes (they currently live in the same in-memory
DuckDB as the data, so they're lost when the process exits) — don't assume they work.
