# Vocabulary

One word per concept, used the same way in Python, the HTTP API, TypeScript, the docs
and the UI. When a new concept needs a name, add it here first. Some code still uses
older words (see "Words to avoid"); rename them when the code is next reorganized.

## Data model

| Term | Meaning |
|---|---|
| **source text** (*text*) | A document's raw text: the `text` parameter of `SourceText`, and `"text"` in search. |
| **document** | One source text plus its field values and note. |
| **document id** | A document's id: from `doc_id=`, else its position (0, 1, ...). Stored as a string. |
| **field** | One named set of values, at most one value per document (`prediction`, `toxicity`, ...). |
| **field name** | A field's name, shown raw in the UI (no prettified display names). |
| **field type** | The class a field's values are wrapped in: `LabelType`, `ScoreType`, `SpanType`, `TemporalType`, `TextType`, `Point2DType` (`_PrimaryType` in code). Also the short form `label`, `score`, `span`, `temporal`, `text`, `point_2d` used by the API and UI. |
| **named field** | A field with its own `SourceText` keyword argument: `prediction`, `confidence`, `gold_label`, `score`, `embedding`, `group`. |
| **custom field** | Any other keyword argument, wrapped in a field type. |
| **label** | A value of a `LabelType` field (`str`, `int` or `bool`); also a span's optional category. |
| **label definition** | What a label value means (`definitions=`, `group_definitions=`). |
| **score** | A number: a `ScoreType` value, or a span's optional score. |
| **point** | A `Point2DType` value, an `(x, y)` pair, e.g. a projected embedding. |
| **group** | A cluster or topic assignment. A `LabelType` field, not a field type of its own. |
| **note** | The user's free text on one document. The only data the user creates. |
| **notes file** | The JSONL file notes are saved to. |
| **orphan note** | A record in the notes file that matches no current document; kept and written back. |

## Spans

| Term | Meaning |
|---|---|
| **span** | A `start`/`end` character range in a document, with optional `label`, `score` and `norm_text`. |
| **span text** | The text a span covers. |
| **norm text** | A span's normalized form (`norm_text`), e.g. an entity's canonical name. |
| **type text** | `norm_text` if set, else the span text. |
| **span type** | (field, type text, label): spans that count as "the same thing". Shown as one badge. |
| **badge** | A span type's chip in the UI, with its count (`Barack Obama PER ×2`). |
| **highlight** | The marked-up spans of a span type in the document text. |

## Filtering

| Term | Meaning |
|---|---|
| **filter** | A condition on one field (`FieldFilter`): op `in` (label values), `range` (score or temporal bounds) or `span` (label, score, text or type text of its spans). |
| **search** | A case-insensitive substring match on the source text and/or text fields (`SearchFilter`, `op: "search"`). Not a filter on one field. |

## Views and data shapes

Views are named by what the user sees; routes may be named by the shape of the data they
return. UI folders and `api/` modules follow the view names.

| View (UI word, folder) | Label in the UI | Data shapes (routes) |
|---|---|---|
| `tabular` | Tabular view | `tabular`: a page of documents with field values |
| `plot` | Plot view | `scatter`: points, from a point field or two score fields; `strip`: one score per document, split by a label field |
| `matrix` | Confusion matrix view | `crosstab`: document counts per pair of values of two label fields |
| `spans` | Span view | `spans`: span and document counts per label and per span type |
| — | Document pane | `documents/{id}`, `documents/{id}/spans`, `documents/{id}/note` |

## Words to avoid

| Avoid | Use instead |
|---|---|
| preset, preset field (incl. `PRESET_*` constants) | named field |
| table view | tabular view |
| typed field, primary type | field / field type |
| cluster type, topic type | group (a label field) |
| entity (outside NER examples) | span |
| crosstab (in UI code) | matrix |
