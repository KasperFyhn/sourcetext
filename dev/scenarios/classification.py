import datetime as dt
import random

from sourcetext import SourceText
from sourcetext.types import TemporalType

_TOPICS = {
    "weather": [
        "The rain kept falling over the harbour",
        "A warm breeze crossed the valley",
        "Snow closed the mountain pass",
    ],
    "politics": [
        "The council debated the new budget",
        "Voters queued outside the town hall",
        "The minister resigned on Tuesday",
    ],
    "travel": [
        "The night train arrived two hours late",
        "We wandered through the old market",
        "The ferry to the island was cancelled",
    ],
}
_POSITIVE = ["and everyone was delighted.", "which turned out wonderfully.", "and the mood was warm."]
_NEGATIVE = ["and people were furious.", "which ended in disaster.", "and the mood was grim."]


def make_source_text(n: int = 120, seed: int = 0) -> SourceText:
    """Synthetic sentiment classification with a topic group and dates.

    Enough documents to span several table pages; some predictions disagree with
    the gold labels so there is something to review.
    """
    rng = random.Random(seed)
    texts, gold, predicted, confidence, topics, dates = [], [], [], [], [], []
    start = dt.date(2020, 1, 1)
    for _ in range(n):
        topic = rng.choice(list(_TOPICS))
        label = rng.choice(["positive", "negative"])
        ending = rng.choice(_POSITIVE if label == "positive" else _NEGATIVE)
        texts.append(f"{rng.choice(_TOPICS[topic])} {ending}")
        gold.append(label)
        wrong = rng.random() < 0.25
        predicted.append(("negative" if label == "positive" else "positive") if wrong else label)
        confidence.append(round(rng.uniform(0.5, 0.75) if wrong else rng.uniform(0.7, 0.99), 3))
        topics.append(topic)
        dates.append(start + dt.timedelta(days=rng.randrange(0, 365 * 3)))

    return SourceText(
        texts=texts,
        predictions=predicted,
        predictions_confidence=confidence,
        gold_labels=gold,
        groups=topics,
        group_definitions={topic: f"Sentences about {topic}." for topic in _TOPICS},
        published=TemporalType(dates),
    )
