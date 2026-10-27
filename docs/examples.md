# Examples

Each example shows one common kind of model output, and what to look at in the app.
See the [API reference](api.md) for every argument and field type.

## Classification with gold labels and confidence

```python
from transformers import pipeline
from sourcetext import SourceText

classify = pipeline("sentiment-analysis")
outputs = classify(texts)

st = SourceText(
    texts,
    prediction=[o["label"] for o in outputs],
    confidence=[o["score"] for o in outputs],
    gold_label=gold_labels,
)
st.start_server()
```

Sort by confidence to read the model's most and least certain calls. The confusion
matrix view opens on gold labels vs. predictions: click an off-diagonal cell to read
the documents the model got wrong. The plot view opens on confidence per gold label,
coloured by prediction, so you can see whether those errors were confident or only
borderline.

## Topic model with group definitions

```python
from bertopic import BERTopic
from sourcetext import ScoreType, SourceText

topic_model = BERTopic()
topics, probs = topic_model.fit_transform(texts)
keywords = {t: ", ".join(w for w, _ in topic_model.get_topic(t)) for t in set(topics)}

st = SourceText(
    texts,
    group=topics,
    group_definitions=keywords,
    topic_probability=ScoreType(probs),
)
st.start_server()
```

Filter to one topic and sort by `topic_probability` to see its most and least typical
documents.

## Document embeddings on a map

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from umap import UMAP
from sourcetext import SourceText

embeddings = SentenceTransformer("all-MiniLM-L6-v2").encode(texts)
clusters = KMeans(n_clusters=8).fit_predict(embeddings)
xy = UMAP().fit_transform(embeddings)

st = SourceText(
    texts,
    group=clusters,
    embedding=xy,
)
st.start_server()
```

In the plot view, pick `embedding` and colour by `group` to see which clusters
the projection keeps together, then click through the points where it doesn't.

## Named entities

```python
import spacy
from sourcetext import SourceText, SpanType

nlp = spacy.load("en_core_web_sm")
entities = [
    [{"start": e.start_char, "end": e.end_char, "label": e.label_, "norm_text": e.lemma_} for e in doc.ents]
    for doc in nlp.pipe(texts)
]

st = SourceText(texts, entities=SpanType(entities))
st.start_server()
```

In the span view, search for a name to see every label the model gave it, then
pick the unexpected one to read those documents with the spans highlighted. Raise
the minimum score (if your spans have one) to see what survives a threshold.

## From a DataFrame, with metadata

```python
from sourcetext import SourceText, TemporalType, TextType

# df has columns: id, text, title, year, prediction, gold
st = SourceText(
    data=df,
    text="text",
    doc_id="id",
    prediction="prediction",
    gold_label="gold",
    title=TextType("title"),
    year=TemporalType("year"),
)
st.start_server()
```
