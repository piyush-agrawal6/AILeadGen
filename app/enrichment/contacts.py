import re
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from app.normalization.phones import normalize_phone

# Priority business role prefixes
PRIORITY_EMAIL_PREFIXES = [
    "info@", "hello@", "contact@", "office@", "sales@",
    "reservations@", "booking@", "admin@", "support@", "enquiries@"
]

# Garbage prefixes or substrings to reject
GARBAGE_EMAIL_PATTERNS = [
    r"^test@", r"^example@", r"^sample@", r"^user@", r"^name@",
    r"^noreply@", r"^no-reply@", r"^do-not-reply@", r"^mailer-daemon@",
    r"^webmaster@", r"^postmaster@", r"@example\.com$", r"@domain\.com$",
    r"@sentry\.", r"@wixpress\.", r"@email\.com$"
]

# File extension false positives (e.g., photo@2x.jpg)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")

# Regex for email in text
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Regex for phone numbers in visible text (North American and International formats)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"
)


class ExtractedContacts:
    def __init__(self):
        self.emails: List[Tuple[str, str, float]] = []  # (email, source_url, confidence)
        self.phones: List[Tuple[str, str, float]] = []  # (phone, source_url, confidence)
        self.contact_forms: List[str] = []
        self.booking_urls: List[str] = []


def is_valid_business_email(email: str) -> bool:
    """Validate that email is not a synthetic test, placeholder, or asset name."""
    if not email or len(email) < 6:
        return False

    clean = email.strip().lower()
    for ext in IMAGE_EXTENSIONS:
        if clean.endswith(ext):
            return False

    for pattern in GARBAGE_EMAIL_PATTERNS:
        if re.search(pattern, clean):
            return False

    return True


def sort_emails_by_priority(emails: List[Tuple[str, str, float]]) -> List[Tuple[str, str, float]]:
    """Sort emails so priority role addresses (info@, hello@, etc.) appear first."""
    def get_sort_key(item: Tuple[str, str, float]) -> int:
        addr = item[0].lower()
        for idx, prefix in enumerate(PRIORITY_EMAIL_PREFIXES):
            if addr.startswith(prefix):
                return idx
        return 99

    # Deduplicate by address
    seen = set()
    deduped = []
    for item in sorted(emails, key=get_sort_key):
        addr = item[0].lower()
        if addr not in seen:
            seen.add(addr)
            deduped.append(item)
    return deduped


def extract_contacts_from_html(
    html: str,
    page_url: str,
    default_country_code: str = "1",
) -> ExtractedContacts:
    """Extract public emails, phones, contact forms, and booking links from HTML."""
    result = ExtractedContacts()
    if not html:
        return result

    soup = BeautifulSoup(html, "lxml")

    # 1. Mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            raw_email = href[7:].split("?")[0].strip()
            if is_valid_business_email(raw_email):
                result.emails.append((raw_email.lower(), page_url, 1.0))

        elif href.lower().startswith("tel:"):
            raw_phone = href[4:].split("?")[0].strip()
            norm = normalize_phone(raw_phone, default_country_code)
            if norm:
                result.phones.append((norm, page_url, 1.0))

        # Booking link heuristic
        lower_href = href.lower()
        link_text = a.get_text().strip().lower()
        if any(w in lower_href or w in link_text for w in ["opentable.com", "resy.com", "sevenrooms.com", "tablecheck.com", "booking.com", "book-now", "reservations", "reserve"]):
            if href.startswith("http"):
                result.booking_urls.append(href)
            elif not href.startswith("#") and not href.startswith("javascript:"):
                result.booking_urls.append(urljoin(page_url, href))

    # 2. Search visible text for emails
    # Remove script and style tags first
    for s in soup(["script", "style", "noscript"]):
        s.decompose()

    text = soup.get_text(separator=" ")
    for match in EMAIL_REGEX.findall(text):
        if is_valid_business_email(match):
            result.emails.append((match.lower(), page_url, 0.8))

    # 3. Detect Contact Forms
    for form in soup.find_all("form"):
        inputs = form.find_all(["input", "textarea"])
        has_email_field = any(
            i.get("type") == "email" or "email" in i.get("name", "").lower()
            for i in inputs
        )
        has_message_field = any(
            i.name == "textarea" or "message" in i.get("name", "").lower() or "comment" in i.get("name", "").lower()
            for i in inputs
        )
        if has_email_field or has_message_field:
            action = form.get("action", "")
            form_url = urljoin(page_url, action) if action else page_url
            result.contact_forms.append(form_url)

    # If the page itself is /contact and has any form
    if "/contact" in page_url.lower() and soup.find("form"):
        result.contact_forms.append(page_url)

    # 4. Search text for phone numbers
    for p_match in PHONE_REGEX.findall(text):
        clean_p = re.sub(r"[^\d+]", "", p_match)
        if 9 <= len(clean_p) <= 15:
            norm_p = normalize_phone(p_match, default_country_code)
            if norm_p:
                result.phones.append((norm_p, page_url, 0.7))

    # Sort & deduplicate emails
    result.emails = sort_emails_by_priority(result.emails)

    # Deduplicate phones
    seen_phones = set()
    deduped_phones = []
    for p, u, conf in result.phones:
        if p not in seen_phones:
            seen_phones.add(p)
            deduped_phones.append((p, u, conf))
    result.phones = deduped_phones

    # Deduplicate contact forms & booking URLs
    result.contact_forms = list(dict.fromkeys(result.contact_forms))
    result.booking_urls = list(dict.fromkeys(result.booking_urls))

    return result
