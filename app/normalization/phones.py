import re
from typing import Optional


def normalize_phone(phone_str: Optional[str], default_country_code: str = "1") -> Optional[str]:
    """Normalize phone string into comparable digits (e.g. +15125550199 or 5125550199)."""
    if not phone_str:
        return None

    cleaned = phone_str.strip()
    if not cleaned:
        return None

    has_leading_plus = cleaned.startswith("+")

    # Extract all digits
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return None

    # Common North American format: 10 digits without leading 1, or 11 digits with leading 1
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    elif has_leading_plus:
        return f"+{digits}"
    elif len(digits) >= 9:
        return f"+{digits}"

    return digits if len(digits) >= 7 else None
