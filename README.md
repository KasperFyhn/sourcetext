# sourcetext

## Primary input types

| Type           | Expected Data                                             | UI Treatment                                       | Use case(s)                                        | Required secondary type |
|----------------|-----------------------------------------------------------|----------------------------------------------------|----------------------------------------------------|-------------------------|
| `TextType`     | text: str                                                 | read-only text                                     | descriptions, source metadata                      |                         |
| `LabelType`    | categorical: int, str, bool)                              | colored badges, filter dropdown                    | classification                                     |                         |
| `ScoreType`    | numerical: float, int                                     | range slider/filter, sortable                      | sentiment scores, classification confidence scores |                         |
| `GroupType`    | categorical (int, str)                                    | sidebar group filter, shows group definition label | clustering, topic modeling                         | `GroupDefinition`       |
| `SpanType`     | offsets + label (dict)                                    | inline highlight in text                           | NER, specific occurrences                          |                         |
| `TemporalType` | orderable (integer, `datetime.Date`, `datetime.DateTime`) | sort axis, timeline                                | metadata, sequence ordering                        |                         |

## Secondary input types

| Type              | Expected Data | UI Treatment                       | Use case(s)                |
|-------------------|---------------|------------------------------------|----------------------------|
| `GroupDefinition` | dict          | Group definition subpage and cards | clustering, topic modeling |

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

st = SourceText(texts, predictions=predictions, confidence_scores=conf_scores, gold=gold_labels)
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

st = SourceText(texts, group=topic_assignment, group_defs=topics)
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```

## Dataframe with predictions, gold labels and metadata

```python
from sourcetext import SourceText

df = ...  # data frame with columns: id, text, year, prediction, gold

st = SourceText(data=df, texts="text", predictions="prediction", gold="gold", ids="id", year="year")
st_server = st.serve(port=8001)
# visit localhost:8001
st_server.stop()
```
