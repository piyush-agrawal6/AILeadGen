import re
import unicodedata
from typing import Optional
from rapidfuzz import fuzz

# Common business suffixes to strip for normalized comparison
BUSINESS_SUFFIXES = [
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bllc\.?\b",
    r"\bl\.l\.c\.?\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\bplc\.?\b",
    r"\bgmbh\b",
    r"\bsarl\b",
    r"\bsa\b",
    r"\bpty\b",
    r"\bgroup\b",
    r"\bholdings\b",
]

_SUFFIX_REGEX = re.compile(
    r"(" + "|".join(BUSINESS_SUFFIXES) + r")$",
    re.IGNORECASE
)


def normalize_business_name(name: Optional[str]) -> str:
    """Normalize a business name for comparison and deduplication."""
    if not name:
        return ""

    # Unicode normalization (NFKD)
    normalized = unicodedata.normalize("NFKD", name)

    # Convert to lowercase
    normalized = normalized.lower()

    # Replace ampersands with 'and'
    normalized = re.sub(r"&", " and ", normalized)

    # Remove apostrophes (e.g. McDonald's -> mcdonalds, Joe's -> joes)
    normalized = re.sub(r"['’`]", "", normalized)

    # Replace punctuation and special characters with whitespace
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    # Collapse multiple whitespaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Strip trailing corporate suffixes
    clean_suffix = _SUFFIX_REGEX.sub("", normalized).strip()
    if clean_suffix:
        normalized = clean_suffix

    # Collapse whitespace again
    return re.sub(r"\s+", " ", normalized).strip()


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate token sort ratio between two business names (0 to 100)."""
    norm1 = normalize_business_name(name1)
    norm2 = normalize_business_name(name2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 100.0
    return float(fuzz.token_sort_ratio(norm1, norm2))


def clean_text(text: Optional[str]) -> str:
    """Clean arbitrary string: collapse whitespace, strip control characters."""
    if not text:
        return ""
    # Strip non-printable / control characters except standard newlines
    cleaned = "".join(ch for ch in text if ch == "\n" or unicodedata.category(ch)[0] != "C")
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def truncate_text(text: Optional[str], max_len: int = 100, suffix: str = "...") -> str:
    """Truncate text to max_len safely."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)].rstrip() + suffix
