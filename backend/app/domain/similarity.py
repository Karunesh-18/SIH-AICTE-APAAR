"""Name similarity shared by R03 and R08: TF-IDF over character n-grams (2 to 4), cosine score.
Pure: scikit-learn is a numeric library, not a framework. The score depends only on the two
strings, so a flag's number can be reproduced from its evidence."""
from sklearn.feature_extraction.text import TfidfVectorizer


def normalise(s: str | None) -> str:
    return " ".join((s or "").lower().split())


def similarity(a: str | None, b: str | None) -> float:
    x, y = normalise(a), normalise(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    try:
        m = TfidfVectorizer(analyzer="char", ngram_range=(2, 4)).fit_transform([x, y])
    except ValueError:  # no n-grams (one-character names)
        return 0.0
    return float((m[0].multiply(m[1])).sum())  # rows are L2-normalised, so the dot is the cosine
