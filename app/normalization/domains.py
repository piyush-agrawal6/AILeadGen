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


# Recognized social media and networking platform domains (including subdomains)
SOCIAL_PLATFORM_DOMAINS = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "fb.me": "facebook",
    "instagram.com": "instagram",
    "instagr.am": "instagram",
    "linkedin.com": "linkedin",
    "x.com": "x_url",
    "twitter.com": "x_url",
    "t.co": "x_url",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "pinterest.com": "pinterest",
    "pin.it": "pinterest",
    "threads.net": "threads",
}

# Legitimate hosted business platforms that must NEVER be classified as social media
HOSTED_BUSINESS_DOMAINS = {
    "square.site",
    "wixsite.com",
    "wordpress.com",
    "webflow.io",
    "squarespace.com",
    "weebly.com",
    "myshopify.com",
    "godaddysites.com",
    "carrd.co",
    "strikingly.com",
}


def classify_social_platform(url_or_domain: Optional[str]) -> Optional[str]:
    """
    Return the social platform key (e.g. 'facebook', 'instagram', 'x_url')
    if the URL or domain belongs to a social media platform, or None.
    Guarantees that legitimate hosted business platforms (square.site, etc.) return None.
    """
    if not url_or_domain:
        return None

    norm = normalize_domain(url_or_domain)
    if not norm:
        return None

    # Never treat hosted website builders as social platforms
    if norm in HOSTED_BUSINESS_DOMAINS:
        return None

    # Check exact match or root domain
    if norm in SOCIAL_PLATFORM_DOMAINS:
        return SOCIAL_PLATFORM_DOMAINS[norm]

    # Subdomain check (e.g. m.facebook.com, l.instagram.com)
    for plat_domain, plat_key in SOCIAL_PLATFORM_DOMAINS.items():
        if norm == plat_domain or norm.endswith(f".{plat_domain}"):
            return plat_key

    return None


def is_social_platform_domain(url_or_domain: Optional[str]) -> bool:
    """Return True if the domain/URL is a social media platform, False otherwise."""
    return classify_social_platform(url_or_domain) is not None

