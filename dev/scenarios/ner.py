import random

from sourcetext import SourceText
from sourcetext.types import LabelType, SpanType

# Canonical names (the norm text) and the surface forms they appear as.
_PEOPLE = {
    "Ada Lovelace": ["Ada Lovelace", "Lovelace", "Ada"],
    "Charles Babbage": ["Charles Babbage", "Babbage"],
    "Mary Shelley": ["Mary Shelley", "Shelley"],
    "Lord Byron": ["Lord Byron", "Byron"],
    "Hans Christian Ørsted": ["Ørsted", "H.C. Ørsted"],
}
_PLACES = {
    "London": ["London"],
    "Paris": ["Paris"],
    "Geneva": ["Geneva", "Genève"],
    "Copenhagen": ["København", "Copenhagen"],
    "Edinburgh": ["Edinburgh"],
}
_ORGS = {
    "Royal Society": ["the Royal Society"],
    "British Museum": ["the British Museum"],
    "Academy": ["the Academy"],
}
_TEMPLATES = [
    "{per} wrote to {org} from {loc}.",
    "In {loc}, {per} met {per2}.",
    "{org} invited {per} to {loc} and later to {loc2}.",
    "{per} left {loc}.",
]


def _mention(rng: random.Random, label: str, names: dict[str, list[str]]) -> tuple[str, dict]:
    """A surface form of a random name, and its span annotation minus offsets: the
    norm text when it differs from the surface form, and a score. Like model output,
    a label is sometimes wrong or missing, and a score sometimes missing."""
    norm = rng.choice(list(names))
    surface = rng.choice(names[norm])
    roll = rng.random()
    if roll < 0.08:
        label = rng.choice(["PER", "LOC", "ORG", "MISC"])
    elif roll < 0.12:
        label = None
    span = {"label": label, "score": round(rng.random(), 2) if rng.random() < 0.9 else None}
    if surface != norm:
        span["norm_text"] = norm
    return surface, span


def _fill(rng: random.Random, template: str) -> tuple[str, list[dict]]:
    """Fill a template, recording each placeholder's span."""
    sources = {"per": ("PER", _PEOPLE), "loc": ("LOC", _PLACES), "org": ("ORG", _ORGS)}
    text, spans, rest = "", [], template
    while "{" in rest:
        before, _, after = rest.partition("{")
        key, _, rest = after.partition("}")
        surface, span = _mention(rng, *sources[key.rstrip("2")])
        text += before
        spans.append({"start": len(text), "end": len(text) + len(surface), **span})
        text += surface
    text += rest
    return text[0].upper() + text[1:], spans


def make_source_text(n: int = 300, seed: int = 0) -> SourceText:
    """NER-style span annotations with norm texts, plus a document label to filter by."""
    rng = random.Random(seed)
    docs = [_fill(rng, rng.choice(_TEMPLATES)) for _ in range(n)]
    return SourceText(
        texts=[text for text, _ in docs],
        entities=SpanType([spans for _, spans in docs]),
        genre=LabelType([rng.choice(["letter", "diary", "report"]) for _ in range(n)]),
    )
