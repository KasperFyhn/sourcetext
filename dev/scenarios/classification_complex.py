from sourcetext import SourceText
from sourcetext.types import TemporalType

from ._classification import TOPICS, generate


def make_source_text(n: int = 120, seed: int = 0) -> SourceText:
    """Synthetic sentiment classification with gold labels, a topic group and dates.

    Enough documents to span several table pages; some predictions disagree with
    the gold labels so there is something to review.
    """
    data = generate(n, seed)
    return SourceText(
        texts=data.texts,
        predictions=data.predicted,
        predictions_confidence=data.confidence,
        gold_labels=data.gold,
        groups=data.topics,
        group_definitions={topic: f"Sentences about {topic}." for topic in TOPICS},
        published=TemporalType(data.dates),
    )
