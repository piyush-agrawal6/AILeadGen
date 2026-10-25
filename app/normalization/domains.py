import re
from typing import Optional
from app.utils.urls import extract_domain, extract_hostname, sanitize_url


def normalize_domain(url_or_domain: Optional[str]) -> Optional[str]:
    """Normalize a URL or domain string to a clean lowercase registered domain."""
    if not url_or_domain:
        return None

    cleaned = url_or_domain.strip().lower()
    if not cleaned:
        return None

    # Handle common prefixes
    cleaned = re.sub(r"^(https?://)?(www\.)?", "", cleaned)
    # Strip paths, queries, fragments
    cleaned = cleaned.split("/")[0].split("?")[0].split("#")[0].strip()

    # Use tldextract
    dom = extract_domain(cleaned)
    if dom:
        return dom

    # Basic regex fallback
    match = re.match(r"^([a-z0-9-]+(?:\.[a-z0-9-]+)+)", cleaned)
    if match:
        return match.group(1)

    return cleaned if "." in cleaned else None


def clean_website_url(url: Optional[str]) -> Optional[str]:
    """Ensure URL has https/http scheme and is valid."""
    if not url:
        return None
    cleaned = sanitize_url(url)
    return cleaned if cleaned else None
