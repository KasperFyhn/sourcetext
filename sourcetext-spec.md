# `sourcetext` — Technical Specification

## Purpose

A Python library for DH/NLP researchers to return to source text alongside model
output (classification, NER, sentiment, topic assignment, clustering, etc.) and
record interpretive judgments **in situ**, from a script or notebook.

**Core argument:** quantitative NLP output in humanities-driven research only
makes sense under human interpretation. Current tooling makes the
return-to-source-text step high-friction (wide dataframes, scrolling terminal
output), so it may get skipped or done superficially, and the quantitative artifact
quietly becomes the finding instead of the occasion for one. The contribution is
**ergonomic**, not methodological: make the correct scholarly move (read, judge,
revise) the path of least resistance.

**Explicitly out of scope:** this is not a QDA platform. No predefined coding
schemes, no coder IDs, no intercoder reliability tooling, no grounded-theory
apparatus. Keep the API surface small enough that a user with minimal coding
confidence can use it correctly on the first try.

---

## Object model

```python
class SourceText:
    def __init__(
        self,
        texts=None,  # list[str], OR omit if data= is given
        *,
        data=None,  # optional pd.DataFrame; if given, other args are column names
        ids=None,
        predictions=None,
        predictions_confidence=None,
        gold_labels=None,
        scores=None,
        groups=None,
        group_definitions=None,
        **fields,  # named or dynamic typed fields (see Type System)
    ): ...

    def serve(self, port: int | None = None, inline: bool = True) -> "ServerHandle": ...
```

- All named/simple kwargs (`predictions=`, `gold_labels=`, `predictions_confidence=`,
  `groups=`, etc.) are sugar over the typed-field system below —
  `predictions="prediction"` must resolve to exactly the same internal
  representation as `predictions=LabelType("prediction")`. **There must be one
  dispatch path, not two parallel systems for "simple" vs. "expert" usage.**
  Concretely, every named preset is wrapped into its typed-field instance
  *before* dispatch, then handled by the exact same per-type branch (and the
  same `db.add_*` call) that custom `**fields` entries go through.

### Dual input mode

1. **List/array mode** — `texts` is a list of raw strings; other fields are
   parallel lists/arrays of the same length, or bare values matched positionally.
2. **DataFrame mode** — `data=df` is given; `texts`, `predictions`, `gold_labels`,
   `ids`, etc. become **column name strings**, resolved against `data`.

The constructor must detect the active mode from whether `data` is `None` and
validate hard against the wrong shape for that mode (e.g. `data=` present but
`texts` is a list, not a string) — raise a clear, plain-English `TypeError`
rather than allowing an obscure downstream `KeyError`.

Typed field wrappers (see below) must accept **either** a column name (string,
resolved against `data=`) **or** a raw array directly, so the typed/expert path
works identically in both input modes.

### `ServerHandle`

- `serve()` is non-blocking: runs uvicorn in a background thread, auto-selects a
  free port via `socket.bind(("", 0))` if `port=None`.
- Returns a handle with `.url`, `.stop()`, and `_repr_html_` (embeds an iframe
  when running in Jupyter; otherwise `__repr__` just prints the URL).
- Supports context-manager usage (`with st.serve() as handle: ...`) — auto-stops
  on exit. Also register an `atexit` hook as a safety net for scripts that error
  out between `serve()` and `.stop()`.
- Maintain a module-level registry of active handles so re-running a notebook
  cell that calls `.serve()` again tears down the previous server on that object
  first, rather than leaking background threads on stale ports.

---

## Type system

Every field beyond the raw text is a **typed field**. Named kwargs
(`predictions=`, `gold_labels=`, `groups=`) are presets that instantiate one of
these types under the hood; `**fields` allows arbitrary additional typed fields
for expert users, e.g.:

```python
SourceText(data=df, texts="text", predictions="prediction", secondary_label=LabelType("topic_label"))
```

Each type must resolve to a defined UI treatment — this mapping is the actual
payoff of the type system (it tells the frontend *how to render*, not just what
the data is).

### Primary types

| Type | Expected data | UI treatment | Use case(s) | Accepts `definitions=` |
|---|---|---|---|---|
| `LabelType` | categorical: `int`, `str`, `bool` | colored badge, filter dropdown | classification | — |
| `ScoreType` | numerical: `float`, `int` | range slider/filter, sortable | sentiment scores, confidence scores | — |
| `GroupType` | categorical: `int`, `str` | sidebar group filter, shows group definition label | clustering, topic modeling | ✓ |
| `SpanType` | `list[dict]` per instance — offsets + label (an instance may have zero, one, or many spans) | inline highlight in text | NER, specific occurrences | — |
| `TemporalType` | orderable: `int` (year), `datetime.date`, `datetime.datetime` | sort axis / timeline; UI granularity dispatches on the underlying Python type (bare `int` → year-level, no calendar coercion attempted; `date` → day; `datetime` → full timestamp) | metadata, sequence ordering | — |
| `FreeTextType` | `str` | free-form display field | editorial notes, source metadata (read-only, supplied at construction) | — |
| `Point2DType` | `(float, float)` per instance — an (x, y) pair | scatter-plot position | projected document embeddings (UMAP/t-SNE) | — |

### Definitions

A primary type may declare `definition_types` (e.g. `dict`) to accept an
optional `definitions=` kwarg at construction — a mapping keyed by that field's
own values (e.g. `GroupType`'s group ids) to arbitrary, JSON-serializable
definition content: a bare string, or a richer object (keywords, scores, etc.)
for the UI to render. `GroupType` is the only primary type using this in v1
(`definitions={group_id: "a plain string" | {...}}`), shown as a
group-definition subpage/cards when hovering or filtering by group. This
content is not meant to be searched at the DB level, only fetched and
displayed.

**Design contract for Claude Code:** treat "primary type optionally accepting
`definitions=`" as a general internal mechanism (`definition_types` on
`_PrimaryType`), not a `GroupType`-only special case — even though `GroupType`
is the only one using it in v1, other primary types may accept `definitions=`
later (e.g. a `LabelType` paired with a longer hover description).

**Scope boundary:** the type set is closed and fixed for v1 (the table above).
No user-facing plugin/subclassing API for custom types in this version.

### `FreeTextType` vs. interpretive annotation — critical distinction

`FreeTextType` is **user-supplied, read-only metadata** passed in at
construction (e.g. an existing `editorial_note` column). It is **not** the
mechanism for the scholar's interpretive annotation made while reviewing in the
served app.

The **interpretive annotation field is not a constructor input type at all.**
It is a fixed, always-present, writable field owned by the served app itself:

- Every instance gets an editable free-text annotation field in the UI,
  regardless of what typed fields were passed to `SourceText`.
- This field is **not** part of the `Type System` table above and must not be
  implemented via `FreeTextType`.
- Persistence: see Write-back below.

---

## Internal schema

All input modes (list-based, DataFrame-based, typed/expert fields) normalize
into a small set of relational tables — not one wide flat table — defined as
SQLAlchemy ORM models in `schema.py`. Each primary type gets its own table,
with rows discriminated by `field_name` (the constructor kwarg / column name
the field was given under). This means an arbitrary number of fields of the
same type (e.g. a `predictions` and a `secondary_label`, both `LabelType`)
don't collide, and named presets (`predictions`, `gold_labels`,
`predictions_confidence`, `groups`) are not structurally different from
expert-supplied fields — they're just rows with a reserved `field_name`.

`db.py` is the service layer between the two: one `add_*` function per table
(`add_labels`, `add_scores`, `add_groups`, `add_spans`, ...), each taking a
SQLAlchemy `Session` plus parallel `document_ids`/`values`, and
`get_sessionmaker()` builds a session bound to a DuckDB engine (via
`duckdb-engine`), creating the tables if needed. `SourceText.__init__` is the
one dispatch point: field collection (named presets wrapped into their typed
instance, merged with `**fields`), then one loop that resolves each field's
values and calls the `db.add_*` function matching its primary type.

- `documents(id, text)` — one row per input text (called `instance_id` /
  `instances` in earlier drafts of this spec; `schema.py` names it `Document`
  / `documents`).
- `labels(document_id, field_name, value)` — every `LabelType` field,
  including the `predictions` and `gold_labels` presets.
- `scores(document_id, field_name, value)` — `ScoreType` (e.g.
  `predictions_confidence`).
- `groups(document_id, field_name, value)` — `GroupType`.
- `group_definitions(field_name, group_id, definition)` — the `definitions=`
  content for `GroupType` fields, keyed by which field it belongs to (so two
  different `GroupType` fields can each carry their own definitions);
  `definition` is stored as JSON, not plain text, so it can be a bare string
  or a richer object.
- `spans(span_id, document_id, field_name, span_start, span_end, label,
  score)` — `SpanType`, one row per span (a document with zero spans simply
  contributes no rows); `score` is optional per span.
- `temporal_year(document_id, field_name, value)`,
  `temporal_date(document_id, field_name, value)`,
  `temporal_datetime(document_id, field_name, value)` — `TemporalType`, split
  into one table per granularity rather than inferring the underlying Python
  type at query time, so DuckDB columns stay natively typed.
- `points_2d(document_id, field_name, x, y)` — `Point2DType`, e.g. a projected
  document embedding.
- `free_text(document_id, field_name, value)` — `FreeTextType`.

A new primary type needs: a class in `types.py` (validation), a table in
`schema.py` (an SQLAlchemy model, usually via the shared `_ScalarField` mixin
for the common `(document_id, field_name, value)` shape), an `add_*` function
in `db.py`, and one dispatch branch in `SourceText.__init__`'s field loop —
not duplicated logic across the three input-mode code paths, which stay fully
decoupled from field-to-table normalization.

**Known limitation, accepted for now:** this design has not been tested at
large-DB scale — a per-type long/narrow table means wide corpora with many
fields produce many rows per instance. Revisit if it proves to be a problem.

---

## Backend

- **DuckDB**, not SQLite: embedded, no separate server process — but columnar/
  OLAP, matching the actual access pattern (filter by task/label/confidence
  range, paginate) far better at DH-corpus scale. Reads Parquet/CSV/pandas
  directly without an import step.
- **SQLAlchemy** ORM sits between the internal schema and DuckDB: `schema.py`
  defines the tables as declarative models, and `db.get_sessionmaker(url)`
  binds a `sessionmaker` to a DuckDB engine via the `duckdb-engine` dialect
  (defaults to an in-memory DB; accepts any SQLAlchemy URL, e.g. for tests or
  a persistent file).
- **FastAPI** serves paginated, filtered slices on demand
  (`GET /documents?task=ner&label=ORG&limit=50&offset=0`) rather than shipping
  the full corpus to the frontend on load. This is the core reason for the
  local-server architecture over a Jupyter-widget (anywidget) approach: the
  corpus stays server-side and the tool scales to full-size DH datasets.
- Span rendering is a **pure frontend concern**: the API returns
  `(text, [{start, end, label, score}, ...])` per document; the frontend does
  the highlighting. This keeps task heterogeneity out of the backend.

### Write-back / persistence

- Interpretive annotations write to a **sidecar DuckDB table**
  (e.g. `{corpus}.sourcetext_annotations.duckdb`), keyed by `document_id`.
- On `SourceText.__init__`, check for and load this sidecar file if it exists
  next to the source data, so resuming a review session across days/kernel
  restarts is just re-instantiating the object against the same input.
- This table is entirely separate from the typed-field system and from
  `FreeTextType` — it is not something the user configures at construction.

---

## Naming

- Package name: **`sourcetext`** (confirmed available on PyPI at time of
  writing).
- Primary class: `SourceText`.

---

## Non-goals (restate explicitly, this scope was hard-won)

- Not a coding-scheme / grounded-theory / intercoder-reliability tool.
- Not a general error-analysis / model-debugging dashboard (contrast: Zeno,
  LIT, Errudite — different goal, and both Zeno and LIT drifted toward heavy
  web-platform architectures and lost momentum; stay a lightweight, locally-run
  library by design).
- No user-facing plugin API for custom field types in v1.
- No open/emergent coding support — annotation is a single free-text field per
  instance, not a tag/category system.
