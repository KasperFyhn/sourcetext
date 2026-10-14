import random

from sourcetext import SourceText
from sourcetext.types import LabelType, SpanType

_PEOPLE = ["Ada Lovelace", "Charles Babbage", "Mary Shelley", "Lord Byron", "Ørsted"]
_PLACES = ["London", "Paris", "Geneva", "København", "Edinburgh"]
_ORGS = ["the Royal Society", "the British Museum", "the Academy"]
_TEMPLATES = [
    "{per} wrote to {org} from {loc}.",
    "In {loc}, {per} met {per2}.",
    "{org} invited {per} to {loc} and later to {loc2}.",
    "{per} left {loc}.",
]


def _fill(rng: random.Random, template: str) -> tuple[str, list[dict]]:
    """Fill a template, recording each placeholder's span. Sometimes mislabels a
    span, as a model would."""
    values = {
        "per": ("PER", rng.choice(_PEOPLE)),
        "per2": ("PER", rng.choice(_PEOPLE)),
        "loc": ("LOC", rng.choice(_PLACES)),
        "loc2": ("LOC", rng.choice(_PLACES)),
        "org": ("ORG", rng.choice(_ORGS)),
    }
    text, spans, rest = "", [], template
    while "{" in rest:
        before, _, after = rest.partition("{")
        key, _, rest = after.partition("}")
        label, value = values[key]
        text += before
        if rng.random() < 0.1:
            label = rng.choice(["PER", "LOC", "ORG", "MISC"])
        spans.append(
            {"start": len(text), "end": len(text) + len(value), "label": label, "score": round(rng.random(), 2)}
        )
        text += value
    text += rest
    return text[0].upper() + text[1:], spans


def make_source_text(n: int = 300, seed: int = 0) -> SourceText:
    """NER-style span annotations, plus a document label to filter by."""
    rng = random.Random(seed)
    docs = [_fill(rng, rng.choice(_TEMPLATES)) for _ in range(n)]
    return SourceText(
        texts=[text for text, _ in docs],
        entities=SpanType([spans for _, spans in docs]),
        genre=LabelType([rng.choice(["letter", "diary", "report"]) for _ in range(n)]),
    )
