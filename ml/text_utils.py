"""NLP helpers: tokenisation, lexicon sentiment, stylometry, optional spaCy NER.

Runs on the standard library alone. If you set FRD_USE_SPACY=1 and install
`en_core_web_sm`, named-entity counts replace the capitalised-word heuristic
(train and serve with the same setting!).
"""
import os
import re

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STRETCH = re.compile(r"(.)\1{2,}")

POS_WORDS = set("""amazing awesome best brilliant beautiful captivating charming compelling delightful
enjoyable excellent fantastic fun gem good great gripping heartfelt hilarious impressive incredible love
loved lovely masterpiece moving outstanding perfect powerful solid stunning superb terrific thrilling
touching wonderful worth satisfying engaging memorable sharp smart convincing recommended unforgettable
breathtaking stellar""".split())
NEG_WORDS = set("""awful bad boring dull disappointing disappointment disaster horrible hated hate lame mess
mediocre pathetic poor predictable rubbish scam terrible trash waste worst weak flat forgettable tedious
confusing annoying clumsy overlong shallow unwatchable stale garbage ashamed letdown rushed underdeveloped
miscast uninspired incoherent""".split())

GENERIC_PHRASES = [
    "best movie ever", "best film ever", "worst movie ever", "worst film ever", "must watch", "must-watch",
    "must see", "must-see", "highly recommend", "waste of money", "waste of time", "10/10", "0/10",
    "five stars", "zero stars", "masterpiece", "do not watch", "don't miss", "nothing negative",
    "blockbuster", "unforgettable", "stellar performances", "breathtaking", "scam", "garbage", "trash",
    "save your money", "worth every penny", "overall", "nothing negative to say",
]
ASPECT_WORDS = set("""acting actor actress cinematography score soundtrack pacing plot script screenplay
editing dialogue direction director ending twist scene scenes character characters runtime visuals effects
music camera sequence act chemistry""".split())
FIRST_PERSON = {"i", "my", "me", "i'm", "i've", "i'd", "we", "our"}

_SPACY = None


def _get_spacy():
    global _SPACY
    if _SPACY is None:
        try:
            import spacy
            _SPACY = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
        except Exception:  # spaCy or model not installed
            _SPACY = False
    return _SPACY


def use_spacy() -> bool:
    return os.getenv("FRD_USE_SPACY", "0") == "1" and bool(_get_spacy())


def normalize(text: str) -> str:
    """Lowercase + strip punctuation; used for duplicate-text detection."""
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", str(text).lower())).strip()


def _specificity(text: str, sentences) -> int:
    if use_spacy():
        return len(_get_spacy()(text).ents)
    count = 0
    for s in sentences:
        toks = _WORD.findall(s)
        for t in toks[1:]:  # skip sentence-initial capital
            if t[0].isupper() and not t.isupper() and t != "I":
                count += 1
    return count


def text_features(text: str) -> dict:
    text = str(text or "")
    words = _WORD.findall(text)
    lower = [w.lower() for w in words]
    n_words = len(words)
    sentences = [s for s in _SENT_SPLIT.split(text.strip()) if s]
    low_text = text.lower()

    pos = sum(w in POS_WORDS for w in lower)
    neg = sum(w in NEG_WORDS for w in lower)
    letters = [c for c in text if c.isalpha()]
    caps_ratio = (sum(c.isupper() for c in letters) / len(letters)) if letters else 0.0

    return {
        "n_words": n_words,
        "avg_word_len": (sum(map(len, words)) / n_words) if n_words else 0.0,
        "n_sentences": len(sentences),
        "avg_sentence_len": (n_words / len(sentences)) if sentences else 0.0,
        "exclaim_count": text.count("!"),
        "exclaim_ratio": text.count("!") / max(len(text), 1),
        "question_count": text.count("?"),
        "caps_ratio": caps_ratio,
        "all_caps_words": sum(w.isupper() and len(w) > 2 for w in words),
        "stretched_chars": len(_STRETCH.findall(text)),
        "digit_count": sum(c.isdigit() for c in text),
        "lexical_diversity": (len(set(lower)) / n_words) if n_words else 1.0,
        "generic_hits": sum(p in low_text for p in GENERIC_PHRASES),
        "aspect_hits": sum(w in ASPECT_WORDS for w in lower),
        "first_person": sum(w in FIRST_PERSON for w in lower),
        "specificity": _specificity(text, sentences),
        "pos_words": pos,
        "neg_words": neg,
        "sentiment_score": (pos - neg) / (pos + neg + 1.0),
    }
