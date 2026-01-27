import re
import unicodedata


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = normalized.translate(
        str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"})
    )
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


FORBIDDEN_PHRASES = [
    ("racist", True),
    ("nigger", True),
    ("kill all", True),
    ("hate all", True),
    ("child porn", True),
    ("pedo", True),
    ("porn", True),
    ("nsfw", False),
    ("xxx", False),
]

FORBIDDEN_PATTERNS = [
    {
        "phrase": normalize_text(phrase),
        "compact": normalize_text(phrase).replace(" ", ""),
        "allow_compact": allow_compact,
        "pattern": re.compile(rf"\b{re.escape(normalize_text(phrase))}\b"),
    }
    for phrase, allow_compact in FORBIDDEN_PHRASES
]

FORBIDDEN_REGEXES = [
    re.compile(r"n[\W_]*i[\W_]*g[\W_]*g[\W_]*e[\W_]*r", re.IGNORECASE),
    re.compile(r"kill[\W_]*all", re.IGNORECASE),
    re.compile(r"hate[\W_]*all", re.IGNORECASE),
    re.compile(r"child[\W_]*porn", re.IGNORECASE),
]


def is_content_blocked(text: str) -> bool:
    if not text:
        return False

    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")

    for pattern in FORBIDDEN_REGEXES:
        if pattern.search(text):
            return True

    for entry in FORBIDDEN_PATTERNS:
        if entry["pattern"].search(normalized):
            return True
        if entry["allow_compact"] and entry["compact"] and entry["compact"] in compact:
            return True

    return False
