import random

from sourcetext import SourceText
from sourcetext.types import TemporalType, TextType

from ._classification import TOPICS, generate

AUTHORS = ["Ada Lovelace", "Karen Blixen", "Hans Christian Andersen", "Virginia Woolf", "Søren Kierkegaard"]


def make_source_text(n: int = 120, seed: int = 0) -> SourceText:
    """Synthetic sentiment classification with gold labels, a topic group, dates and
    an author per document.

    Enough documents to span several table pages; some predictions disagree with
    the gold labels so there is something to review.
    """
    data = generate(n, seed)
    # A separate generator, so the shared data matches classification_simple's.
    rng = random.Random(seed)
    authors = [rng.choice(AUTHORS) for _ in range(n)]
    return SourceText(
        text=data.texts,
        prediction=data.predicted,
        confidence=data.confidence,
        gold_label=data.gold,
        group=data.topics,
        group_definitions={topic: f"Sentences about {topic}." for topic in TOPICS},
        published=TemporalType(data.dates),
        author_name_long_field=TextType(authors),
    )
