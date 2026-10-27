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
        text=data.texts,
        prediction=data.predicted,
        confidence=data.confidence,
        gold_label=data.gold,
        group=data.topics,
        group_definitions={topic: f"Sentences about {topic}." for topic in TOPICS},
        published=TemporalType(data.dates),
    )
