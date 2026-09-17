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
        texts=None,           # list[str], OR omit if data= is given
        *,
        data=None,             # optional pd.DataFrame; if given, other args are column names
        ids=None,
        predictions=None,
        gold=None,
        **fields,               # named or dynamic typed fields (see Type System)
    ):
        ...

    def serve(self, port: int | None = None, inline: bool = True) -> "ServerHandle":
        ...
```

- All named/simple kwargs (`predictions=`, `gold=`, `confidence=`, `group=`, etc.)
  are sugar over the typed-field system below — `predictions="prediction"` must
  resolve to exactly the same internal representation as
  `predictions=LabelType("prediction")`. **There must be one dispatch path, not
  two parallel systems for "simple" vs. "expert" usage.**

### Dual input mode

1. **List/array mode** — `texts` is a list of raw strings; other fields are
   parallel lists/arrays of the same length, or bare values matched positionally.
2. **DataFrame mode** — `data=df` is given; `texts`, `predictions`, `gold`,
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
(`predictions=`, `gold=`, `group=`) are presets that instantiate one of these
types under the hood; `**fields` allows arbitrary additional typed fields for
expert users, e.g.:

```python
SourceText(data=df, texts="text", predictions="prediction",
           secondary_label=LabelType("topic_label"))
```

Each type must resolve to a defined UI treatment — this mapping is the actual
payoff of the type system (it tells the frontend *how to render*, not just what
the data is).

### Primary types

| Type | Expected data | UI treatment | Use case(s) | Secondary type |
|---|---|---|---|---|
| `LabelType` | categorical: `int`, `str`, `bool` | colored badge, filter dropdown | classification | — |
| `ScoreType` | numerical: `float`, `int` | range slider/filter, sortable | sentiment scores, confidence scores | — |
| `GroupType` | categorical: `int`, `str` | sidebar group filter, shows group definition label | clustering, topic modeling | `GroupDefinition` |
| `SpanType` | `list[dict]` per instance — offsets + label (an instance may have zero, one, or many spans) | inline highlight in text | NER, specific occurrences | — |
| `Temporal` | orderable: `int` (year), `datetime.date`, `datetime.datetime` | sort axis / timeline; UI granularity dispatches on the underlying Python type (bare `int` → year-level, no calendar coercion attempted; `date` → day; `datetime` → full timestamp) | metadata, sequence ordering | — |
| `FreeTextType` | `str` | free-form display field | editorial notes, source metadata (read-only, supplied at construction) | — |

### Secondary types

| Type | Expected data | UI treatment |
|---|---|---|
| `GroupDefinition` | `dict[group_id, str]` | group-definition subpage / cards, shown when hovering or filtering by group |

**Design contract for Claude Code:** treat "primary type optionally paired with
a secondary type" as a general internal mechanism, not a `GroupType`-only
special case — even though `GroupType`/`GroupDefinition` is the only pairing
wired up in v1, other primary types may gain an optional secondary type later
(e.g. a `LabelType` paired with a longer hover description).

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
into a small set of relational tables through one dispatch point in
`SourceText.__init__` (field collection, then one `schema.add_field` call per
field) — not one wide flat table. Each primary type gets its own table, with
rows discriminated by `field_name` (the constructor kwarg / column name the
field was given under). This means an arbitrary number of fields of the same
type (e.g. a `predictions` and a `secondary_label`, both `LabelType`) don't
collide, and named presets (`predictions`, `gold`, `confidence`, `group`) are
not structurally different from expert-supplied fields — they're just rows
with a reserved `field_name`.

- `instances(instance_id, text)`
- `labels(instance_id, field_name, value)` — every `LabelType` field,
  including the `predictions` and `gold` presets.
- `scores(instance_id, field_name, value)` — `ScoreType` (e.g. `confidence`).
- `groups(instance_id, field_name, value)` — `GroupType`.
- `group_definitions(field_name, group_id, definition)` — `GroupDefinition`,
  keyed by which `GroupType` field it belongs to (so two different `GroupType`
  fields can each carry their own definitions).
- `spans(span_id, instance_id, field_name, span_start, span_end, label,
  score)` — `SpanType`, one row per span (an instance with zero spans simply
  contributes no rows); `score` is optional per span.
- `temporal_year(instance_id, field_name, value)`,
  `temporal_date(instance_id, field_name, value)`,
  `temporal_datetime(instance_id, field_name, value)` — `Temporal`, split into
  one table per granularity rather than inferring the underlying Python type
  at query time, so DuckDB columns stay natively typed.
- `free_text(instance_id, field_name, value)` — `FreeTextType`.

A bug fix or new field only needs a new branch in `schema.add_field`, not
duplicated logic across the three input-mode code paths — mode handling
(list vs. DataFrame vs. expert) and field-to-table normalization are fully
decoupled.

**Known limitation, accepted for now:** this design has not been tested at
large-DB scale — a per-type long/narrow table means wide corpora with many
fields produce many rows per instance. Revisit if it proves to be a problem.

---

## Backend

- **DuckDB**, not SQLite: embedded, no separate server process — but columnar/
  OLAP, matching the actual access pattern (filter by task/label/confidence
  range, paginate) far better at DH-corpus scale. Reads Parquet/CSV/pandas
  directly without an import step.
- **FastAPI** serves paginated, filtered slices on demand
  (`GET /instances?task=ner&label=ORG&limit=50&offset=0`) rather than shipping
  the full corpus to the frontend on load. This is the core reason for the
  local-server architecture over a Jupyter-widget (anywidget) approach: the
  corpus stays server-side and the tool scales to full-size DH datasets.
- Span rendering is a **pure frontend concern**: the API returns
  `(text, [{start, end, label, score}, ...])` per instance; the frontend does
  the highlighting. This keeps task heterogeneity out of the backend.

### Write-back / persistence

- Interpretive annotations write to a **sidecar DuckDB table**
  (e.g. `{corpus}.sourcetext_annotations.duckdb`), keyed by `instance_id`.
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
