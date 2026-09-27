from sourcetext import SourceText

from ._classification import generate


def make_source_text(n: int = 120, seed: int = 0) -> SourceText:
    """Synthetic sentiment classification with only predictions and confidence scores:
    the minimal no-ground-truth case."""
    data = generate(n, seed)
    return SourceText(
        texts=data.texts,
        predictions=data.predicted,
        predictions_confidence=data.confidence,
    )
