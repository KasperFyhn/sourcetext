# sourcetext

[![PyPI](https://img.shields.io/pypi/v/sourcetext)](https://pypi.org/project/sourcetext/)
[![CI](https://github.com/KasperFyhn/sourcetext/actions/workflows/ci.yml/badge.svg)](https://github.com/KasperFyhn/sourcetext/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/KasperFyhn/sourcetext/blob/main/LICENSE)

**Return to the source text behind your model output.**

Sometimes, working with and understanding a text corpus requires more than your NLP models' output. It requires inspection of the source text: looking at the documents behind a prediction, a cluster, or an
outlier score.

`sourcetext` gives you that in three lines of Python code. Hand it your texts and
your model's output (labels, scores, clusters, embeddings, dates), and it opens a
local web app where you can navigate your documents by their annotations and read each one in full.

## Quickstart
Install with `pip`:

```bash
pip install sourcetext
```

Then integrate in your NLP workflow.
```python
from sourcetext import SourceText

texts = [
    "The harvest failed for the third year running.",
    "A new bridge was opened to great celebration.",
    "Grain prices rose sharply in the spring.",
]
predictions = ["negative", "positive", "negative"]

st = SourceText(texts, prediction=predictions)
st.start_server()  # then open http://localhost:8001
```

And dive into the source text in a simple UI in your browser.

![The sourcetext app](https://raw.githubusercontent.com/KasperFyhn/sourcetext/main/screenshot.png)

In a script, `start_server()` blocks until you press Ctrl+C. In Jupyter it runs in
the background, so you can keep working and call `st.stop_server()` when done.

The app has:

- **Table view**: sort, search and filter documents by any field.
- **Plot view**: embeddings, or any two fields against each other.
- **Confusion matrix view**: cross two label fields, click a cell to read its documents.
- **Span view**: find documents by their span annotations (e.g. NER).
- **Document pane**: read a document in full, with all its field values.
- **Notes**: write a note on any document, saved to a JSONL file.

## Fields

Everything you pass beyond the texts is a **field**: one value per document. The
common cases have named arguments (`prediction=`, `confidence=`, `gold_label=`,
`score=`, `embedding=`, `group=`). Any other keyword argument adds a field with
that name, wrapped in its type:

```python
from sourcetext import LabelType, ScoreType, SourceText

SourceText(
    texts,
    prediction=preds,
    toxicity=ScoreType(toxicity_scores),
    genre=LabelType(genres),
)
```

| Type           | Values                                     | Typical use                            |
|----------------|--------------------------------------------|----------------------------------------|
| `TextType`     | `str`                                      | titles, authors, source metadata       |
| `LabelType`    | `str`, `int`, `bool`                       | classes, gold labels, clusters, topics |
| `ScoreType`    | `float`, `int`                             | confidence, sentiment, any metric      |
| `TemporalType` | year (`int`), `date`, `datetime`           | publication year, timestamps           |
| `Point2DType`  | `(x, y)` pair of numbers                   | UMAP / t-SNE embedding projections     |
| `SpanType`     | list of `{"start", "end", ...}` dicts      | named entities, marked passages        |

Every argument also takes a column name when you pass a DataFrame as `data=`.

## Documentation

- [Examples](https://github.com/KasperFyhn/sourcetext/blob/main/docs/examples.md):
  classification, topic models, embeddings, named entities, DataFrames.
- [API reference](https://github.com/KasperFyhn/sourcetext/blob/main/docs/api.md):
  `SourceText`'s arguments, field types, label definitions, serving the app.
- [Notes](https://github.com/KasperFyhn/sourcetext/blob/main/docs/notes.md):
  where notes are saved and how they're matched back to documents.

## Project status

sourcetext is in early development (alpha). The API may change between releases,
and some parts are not built yet:

See the [roadmap](https://github.com/KasperFyhn/sourcetext/blob/main/ROADMAP.md) for
what's planned next.

Feedback and issues are very welcome at
[github.com/KasperFyhn/sourcetext/issues](https://github.com/KasperFyhn/sourcetext/issues).

## Contributing

Development setup, the architecture, and how the Python package and the React
frontend fit together are described in
[CLAUDE.md](https://github.com/KasperFyhn/sourcetext/blob/main/CLAUDE.md). In short:

```bash
pip install -e ".[dev]"
pre-commit install
pytest
./scripts/dev.sh classification_simple   # API + hot-reloading UI on a mock dataset
```

## License

MIT
