# API reference

## `SourceText`

```python
SourceText(
    text,
    *,
    data=None,
    doc_id=None,
    prediction=None,
    confidence=None,
    gold_label=None,
    score=None,
    embedding=None,
    group=None,
    group_definitions=None,
    notes_file=None,
    **fields,
)
```

`text` is the only required argument. Everything else attaches a **field** to the
documents: one value per document, shown as a column in the table and as a row in
the document pane. `notes_file=` is where your notes are saved; see [Notes](notes.md).

### Two ways to pass data

Every argument takes either **an array of values** (one per text, in the same
order: a list, numpy array or pandas Series), or, when `data=` is given, **the name
of a column** in that DataFrame. Pick one mode per call:

```python
# Lists
SourceText(texts, prediction=preds)

# DataFrame columns
SourceText(data=df, text="text", prediction="pred")
```

Missing values can be given as `None`, and pandas' `NaN`/`NaT`/`pd.NA` are treated
the same way. Numpy and pandas values (e.g. `np.float32` scores, `np.datetime64`
dates) are converted to their plain Python equivalents.

### Document IDs

By default documents are numbered `0, 1, 2, …`. Pass `doc_id=` (ints or strings) to
use your own, e.g. to match document IDs elsewhere in your pipeline.

### Named fields

These cover the common cases, and need no wrapping:

| Argument            | Field type    | For                                            |
|---------------------|---------------|------------------------------------------------|
| `prediction`        | `LabelType`   | a classifier's predicted labels                |
| `confidence`        | `ScoreType`   | the classifier's confidence in each prediction |
| `gold_label`        | `LabelType`   | reference / ground-truth labels                |
| `score`             | `ScoreType`   | any single numeric score, e.g. sentiment       |
| `embedding`         | `Point2DType` | a 2D projection of document embeddings         |
| `group`             | `LabelType`   | cluster or topic assignments                   |
| `group_definitions` | —             | what each group means (see below)              |

### Custom fields

Any other keyword argument adds a field with that name. Wrap its values (or its
column name) in a field type, so sourcetext knows how to store, display and filter
it:

```python
from sourcetext import ScoreType, LabelType

SourceText(
    texts,
    toxicity=ScoreType(toxicity_scores),
    genre=LabelType("genre"),  # column name, with data=
)
```

## Field types

| Type           | Values                                               | In the app                                                    | Typical use                            |
|----------------|------------------------------------------------------|---------------------------------------------------------------|----------------------------------------|
| `TextType`     | `str`                                                | shown as text; searchable                                     | titles, authors, source metadata       |
| `LabelType`    | `str`, `int`, `bool`                                 | badge; filter by value; plot axis or colour; confusion matrix | classes, gold labels, clusters, topics |
| `ScoreType`    | `float`, `int`                                       | filter by range; plot axis                                    | confidence, sentiment, any metric      |
| `TemporalType` | `int` (a year), `datetime.date`, `datetime.datetime` | filter by range                                               | publication year, timestamps           |
| `Point2DType`  | `(x, y)` pair of numbers                             | position in the plot                                          | UMAP / t-SNE embedding projections     |
| `SpanType`     | list of `{"start", "end"}` dicts, see below          | badges; filter by label, score, text; span view               | named entities, marked passages        |

All columns in the table view are sortable, except 2D points and spans.

Notes on specific types:

- **`TemporalType`**: all values in one field must share a type. Plain ints are
  treated as years.
- **`SpanType`**: each document gets a list of spans (possibly empty). `start` and
  `end` are character offsets into the text. Optionally, a span has a `label`
  (string), a `score` (number) and a `norm_text` (string: a normalized form of the
  text it covers, e.g. an entity's canonical name); each may be missing or `None`.
  Spans with the same `norm_text` (or covered text, without one) and label are
  shown as one badge, e.g. `Barack Obama PER ×2` for "Obama" and "Barack Obama".
  Filtering spans by label, score or text also hides the spans that don't match
  from badges, counts and highlights.
- **`Point2DType`**: to plot two separate scores against each other instead, just
  pass them as two `ScoreType` fields and pick both as axes in the plot view.

### Label definitions

`LabelType` accepts a `definitions=` dict mapping each value to what it means: a
codebook entry for an annotation category, or a topic's keywords. That can be a
plain string, or any JSON-serializable object (e.g. keywords with weights).
`group_definitions=` is shorthand for attaching one to `group=`:

```python
# These are equivalent:
SourceText(texts, group=topics, group_definitions=keywords)
SourceText(texts, group=LabelType(topics, definitions=keywords))

# Other label fields take definitions= directly, e.g. a codebook:
SourceText(
    texts,
    gold_label=LabelType(gold, definitions={"irony": "Says the opposite of what is meant"}),
    era=LabelType(eras, definitions={"early": "before 1850", "late": "1850 and after"}),
)
```

In the app, a value with a definition is marked with an ⓘ wherever it appears
(badges, filter options, plot legends and axes, confusion matrix headers): hover
the ⓘ to see the definition.
Keyword lists, as `[word, weight]` pairs or a `{word: weight}` dict, are shown as
a table of words and weights.

## Serving the app

```python
st.start_server(port=8001, block=None)
st.stop_server()
```

- `port`: where the app is served, at `http://localhost:<port>`.
- `block`: `True` blocks until Ctrl+C (for scripts). `False` runs the server in
  the background (for Jupyter and other running event loops). The default `None`
  picks the right one automatically.
