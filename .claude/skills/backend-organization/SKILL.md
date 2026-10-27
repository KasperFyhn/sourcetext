---
name: backend-organization
description: Principles for where Python code goes and how it is split in sourcetext/ and tests/. Use when adding, splitting, moving or renaming routes, queries, schema tables, field types, helpers or tests, or when reorganizing the backend.
---

# Backend code organization

Principles for `sourcetext/` and `tests/`. Apply them to new code; when touching old code
that breaks them, move it in a separate commit (see "Moves" below).

## Target layout

```
sourcetext/
  __init__.py  sourcetext.py  types.py  notes.py
  db/
    engine.py  schema.py  population.py
    queries/            # read helpers, split by concern
      __init__.py       # re-exports the public API
      filters.py        # filter dataclasses, applying filters, span/search conditions
      fields.py  documents.py  plots.py  spans.py  notes.py
  server/
    app.py  backgroundserver.py  requests.py
    routes/
      documents.py  plots.py  spans.py  notes.py
tests/
  test_types.py  test_sourcetext.py  test_population.py  test_notes.py
  server/
    test_documents.py  test_plots.py  test_spans.py  test_notes.py
```

## Principles

1. **Layers:** `routes → db.queries → db.schema`. Routes parse the request and shape the
   response; they don't build SQLAlchemy queries. Queries return dataclasses, not ORM
   objects.
   *Why:* query logic can be tested without HTTP, and routes stay thin.
2. **Query modules split by concern, matching the routes** (`plots.py` serves
   scatter/strip/crosstab, `spans.py` the span view, and so on). Filtering is shared by
   all of them, so it gets its own `filters.py`.
   *Why:* one 700-line `queries.py` holding every view is hard to navigate.
3. **One route module per resource**, matching the UI's `api/` modules. Keep the rule
   that literal paths (`tabular`, `scatter`, `fields`, ...) register before
   `{document_id}` ones, and that routes are `async def`.
   *Why:* a route and its client code are easy to find from each other.
4. **Private helpers stay private.** A `_helper` needed by a second module gets a public
   name in a shared module (often `filters.py`), instead of being imported across
   modules with its underscore.
   *Why:* the underscore should mean "only used here".
5. **Keep the per-type layering.** A field type is one entry in each layer (`types.py`,
   `db/schema.py`, `db/population.py`, the dispatch in `sourcetext.py`), not a folder
   per type. See CLAUDE.md's "Adding a new field type".
   *Why:* each layer stays uniform, and comparing types is easy.
6. **Tests mirror modules.** Server tests live in `tests/server/`, one file per route
   module; shared fixtures go in `conftest.py`.
   *Why:* finding a module's tests shouldn't mean searching an 800-line file.

## Applies to both frontend and backend

- **One name per concept, from `VOCABULARY.md`.** Routes may name the data shape they
  return (`scatter`, `strip`, `crosstab`); query and route modules otherwise follow the
  view names (`tabular`, `plot`, `matrix`, `spans`). A new concept gets its name added
  there first.
- **Size is a signal, not a rule.** A file past ~300 lines is a prompt to check whether
  it holds more than one concern.
- **Moves are separate commits** from behaviour changes, so the diff is pure moves and
  renames. Keep public imports working via re-exports (e.g. `db/queries/__init__.py`)
  only where something outside the module uses them; no deprecation shims needed
  (the package is pre-release).
- **Docs follow the code.** A move updates paths in `CLAUDE.md` and `docs/` in the same
  change.

## Where does new backend code go?

- A new route → the route module for its resource; its query → the matching
  `db/queries/` module; its test → `tests/server/test_<resource>.py`.
- A new filter kind → `db/queries/filters.py` (and its request model in
  `server/requests.py`).
- A new field type → one entry per layer (principle 5) plus the docs/README tables.
- After adding or moving files: `ruff check .`, `ruff format .`, `pytest`.
