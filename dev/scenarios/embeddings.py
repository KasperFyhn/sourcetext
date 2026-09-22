import random

from sourcetext import SourceText
from sourcetext.types import GroupType, Point2DType, ScoreType

_SUBJECTS = ["The curator", "A visiting scholar", "The conservator", "An unnamed donor", "The museum director"]
_VERBS = ["catalogued", "restored", "appraised", "photographed", "mislabelled"]
_OBJECTS = ["the ceramic shard", "the oil portrait", "the bronze coin", "the manuscript leaf", "the woven textile"]

# Well-separated Gaussian blobs, each tied to a group label, so the scatter view has
# visible cluster structure to verify against (rather than uniform noise) and the
# "color by group" feature has clusters that visibly line up with their color.
_CLUSTERS = [
    ("ceramics", -4.0, 3.0),
    ("paintings", 5.0, 4.0),
    ("coins", 0.5, -5.0),
]
_CLUSTER_SPREAD = 1.1


def make_source_text(n: int = 150, seed: int = 0) -> SourceText:
    """An embedding field (three visible clusters, with a few coincident points to
    exercise the scatter view's multipoint hover) plus two score fields for the
    score-pair scatter mode, plus a group field (one group per cluster, with a few
    documents left ungrouped) for the "color by group" feature."""
    rng = random.Random(seed)
    texts, embedding, confidence, readability, collection = [], [], [], [], []

    for i in range(n):
        texts.append(f"{rng.choice(_SUBJECTS)} {rng.choice(_VERBS)} {rng.choice(_OBJECTS)}.")

        label, cx, cy = rng.choice(_CLUSTERS)
        # Force a handful of points onto identical coordinates so a "multipoint"
        # (several documents at the same spot) is always present to hover over.
        if i % 17 == 0:
            embedding.append((cx, cy))
        else:
            embedding.append((round(rng.gauss(cx, _CLUSTER_SPREAD), 3), round(rng.gauss(cy, _CLUSTER_SPREAD), 3)))

        confidence.append(round(rng.uniform(0.4, 0.99), 3))
        # Leave a handful of readability scores unset to exercise the score-pair
        # endpoint's inner-join (documents missing either score are omitted).
        readability.append(None if rng.random() < 0.1 else round(rng.uniform(20, 90), 1))
        # Leave a handful of documents ungrouped to exercise the scatter color
        # scale's "(no group)" bucket.
        collection.append(None if rng.random() < 0.1 else label)

    return SourceText(
        texts=texts,
        embedding=Point2DType(embedding),
        confidence=ScoreType(confidence),
        readability=ScoreType(readability),
        collection=GroupType(collection),
    )
