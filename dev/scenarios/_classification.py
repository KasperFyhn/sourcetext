"""Shared synthetic sentiment data for the classification scenarios (not a scenario
itself: dev/serve.py skips modules starting with an underscore)."""

import datetime as dt
import random
from dataclasses import dataclass, field

TOPICS = {
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


@dataclass
class ClassificationData:
    texts: list[str] = field(default_factory=list)
    gold: list[str] = field(default_factory=list)
    predicted: list[str] = field(default_factory=list)
    confidence: list[float] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    dates: list[dt.date] = field(default_factory=list)


def generate(n: int, seed: int) -> ClassificationData:
    """Sentiment sentences where ~25% of predictions disagree with the gold label,
    with lower confidence on the wrong ones, so there is something to review."""
    rng = random.Random(seed)
    data = ClassificationData()
    start = dt.date(2020, 1, 1)
    for _ in range(n):
        topic = rng.choice(list(TOPICS))
        label = rng.choice(["positive", "negative"])
        ending = rng.choice(_POSITIVE if label == "positive" else _NEGATIVE)
        data.texts.append(f"{rng.choice(TOPICS[topic])} {ending}")
        data.gold.append(label)
        wrong = rng.random() < 0.25
        data.predicted.append(("negative" if label == "positive" else "positive") if wrong else label)
        data.confidence.append(round(rng.uniform(0.5, 0.75) if wrong else rng.uniform(0.7, 0.99), 3))
        data.topics.append(topic)
        data.dates.append(start + dt.timedelta(days=rng.randrange(0, 365 * 3)))
    return data
