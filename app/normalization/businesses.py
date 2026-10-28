from app.database.models import Business
from app.normalization.domains import (
    classify_social_platform,
    clean_website_url,
    is_social_platform_domain,
    normalize_domain,
)
from app.normalization.phones import normalize_phone
from app.utils.text import clean_text, normalize_business_name


def normalize_business(b: Business) -> Business:
    """Normalize a Business instance fields for deduplication and consistent storage."""
    b.name = clean_text(b.name)
    b.normalized_name = normalize_business_name(b.name)

    if b.website:
        b.website = clean_website_url(b.website)
        b.domain = normalize_domain(b.website)
    elif b.domain:
        b.domain = normalize_domain(b.domain)

    # Check if the website is actually a social media profile
    social_key = classify_social_platform(b.website or b.domain)
    if social_key:
        if hasattr(b, social_key) and not getattr(b, social_key) and b.website:
            setattr(b, social_key, b.website)
        b.website = None
        b.domain = None

    if b.website and b.website.lower().strip() in ("nan", "none", "null"):
        b.website = None
        b.domain = None

    if b.phone:
        if b.phone.lower().strip() in ("nan", "none", "null"):
            b.phone = None
            b.normalized_phone = None
        else:
            b.normalized_phone = normalize_phone(b.phone, default_country_code=b.country_code or "1")

    if b.public_email:
        cleaned_em = b.public_email.strip().lower()
        if cleaned_em in ("nan", "none", "null"):
            b.public_email = None
        else:
            b.public_email = cleaned_em

    if b.city:
        b.city = clean_text(b.city)
    if b.address:
        b.address = clean_text(b.address)

    return b
