# sourcetext

Return to source text alongside NLP model output and record interpretive judgments in situ.

```bash
pip install sourcetext
```

## Primary input types

| Type           | Expected Data                                             | UI Treatment                                       | Use case(s)                                        | Accepts `definitions=` |
|----------------|-----------------------------------------------------------|----------------------------------------------------|----------------------------------------------------|-------------------------|
| `FreeTextType` | text: str                                                 | read-only text                                     | descriptions, source metadata                      |                         |
| `LabelType`    | categorical: int, str, bool)                              | colored badges, filter dropdown                    | classification                                     |                         |
| `ScoreType`    | numerical: float, int                                     | range slider/filter, sortable                      | sentiment scores, classification confidence scores |                         |
| `GroupType`    | categorical (int, str)                                    | sidebar group filter, shows group definition label | clustering, topic modeling                         | ✓                       |
| `SpanType`     | offsets + label (dict)                                    | inline highlight in text                           | NER, specific occurrences                          |                         |
| `TemporalType` | orderable (integer, `datetime.date`, `datetime.datetime`) | sort axis, timeline                                | metadata, sequence ordering                        |                         |
| `Point2DType`  | `(float, float)` — an (x, y) pair                         | scatter-plot position                              | projected document embeddings (UMAP/t-SNE)         |                         |

## `definitions=`

`GroupType` accepts an optional `definitions=` dict mapping each group id to
a definition — a plain string, or a richer JSON-serializable object (e.g.
keywords, scores) for the UI to render as a group-definition subpage/cards.
The constructor's `group_definitions=` kwarg is sugar that attaches this to
a `groups=` field passed by name.

## Classification with no ground-truth

```python
from sourcetext import SourceText

texts = [...]
# init and configure classifier
# ...
predictions = classifier(texts)

st = SourceText(texts, predictions=predictions)
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```

## Classification with ground-truth and confidence scores

```python
from sourcetext import SourceText

gold_labels = [...]

texts = [...]
# init and configure classifier
# ...
predictions_with_conf_scores = classifier(texts)
predictions, conf_scores = zip(*predictions_with_conf_scores)

st = SourceText(texts, predictions=predictions, predictions_confidence=conf_scores, gold_labels=gold_labels)
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```

## Clustering with data about topic groups

```python
from sourcetext import SourceText

texts = [...]
# init and configure topic model
# ...
topics, topic_assignment = topic_model.fit(texts)

st = SourceText(texts, groups=topic_assignment, group_definitions=topics)
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```

## Dataframe with predictions, gold labels and metadata

```python
from sourcetext import SourceText, TemporalType

df = ...  # data frame with columns: id, text, year, prediction, gold

st = SourceText(
    data=df,
    texts="text",
    predictions="prediction",
    gold_labels="gold",
    ids="id",
    year=TemporalType("year"),  # custom fields (anything beyond the named presets) need explicit wrapping
)
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```
