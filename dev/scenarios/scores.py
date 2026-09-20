import random

from sourcetext import SourceText
from sourcetext.types import ScoreType

_SUBJECTS = ["The committee", "A local newspaper", "The author", "An anonymous letter", "The publisher"]
_VERBS = ["described", "criticised", "praised", "summarised", "questioned"]
_OBJECTS = ["the new translation", "the parish records", "the winter exhibition", "the reform proposal", "the archive"]


def make_source_text(n: int = 200, seed: int = 0) -> SourceText:
    """Several independent score fields (no classification), many documents."""
    rng = random.Random(seed)
    texts = [f"{rng.choice(_SUBJECTS)} {rng.choice(_VERBS)} {rng.choice(_OBJECTS)}." for _ in range(n)]

    return SourceText(
        texts=texts,
        scores=[round(rng.random(), 3) for _ in range(n)],
        toxicity=ScoreType([round(rng.random() ** 3, 3) for _ in range(n)]),
        readability=ScoreType([round(rng.uniform(20, 90), 1) for _ in range(n)]),
    )
