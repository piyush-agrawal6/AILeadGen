import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Generic platform roots and non-profile paths to ignore
IGNORED_PATHS = {
    "", "/", "share", "sharer", "intent", "home", "login", "signup", "search",
    "pages", "p", "reel", "stories", "hashtag", "explore", "about", "help",
    "privacy", "terms", "policies", "groups", "watch", "dialog", "plugins",
    "widgets", "directory", "places", "fundraisers", "voting", "portal",
    "safety", "transparency", "cookies", "cookie", "ads", "business",
    "creators", "developers", "security", "community", "guidelines", "status",
    "government-nonprofits", "meta-for-business", "profile.php", "home.php"
}

GENERIC_OR_PLATFORM_HANDLES = {
    # Platform / Corporate entities
    "meta", "facebook", "instagram", "linkedin", "twitter", "x", "youtube", "tiktok", "pinterest", "threads",
    "whatsapp", "messenger", "google", "apple", "microsoft",
    # Platform Help / Corporate departments
    "help", "support", "about", "privacy", "terms", "policies", "legal", "careers", "press", "blog",
    "developers", "security", "community", "guidelines", "status", "safety", "transparency", "cookies",
    "cookie", "ads", "business", "creators", "login", "signup", "recover", "settings", "marketplace",
    "government-nonprofits", "government", "nonprofit", "nonprofits", "meta-for-business",
}


def is_valid_social_handle(handle: str) -> bool:
    """Validate that a handle is a legitimate business entity and not a platform artifact or locale."""
    if not handle or len(handle) < 2:
        return False

    clean_h = handle.lower().strip("@/.")
    if clean_h in IGNORED_PATHS or clean_h in GENERIC_OR_PLATFORM_HANDLES:
        return False

    # Check for locale or language codes (e.g. fr-fr, en-us, es, fr, de, pt-br)
    if re.match(r"^[a-z]{2}(-[a-z]{2,4})?$", clean_h):
        return False

    return True


def _legacy_extract_social_links(urls: List[str]) -> Dict[str, str]:
    """Extract and normalize public business social media profiles from a list of URLs."""
    socials: Dict[str, str] = {}

    for raw_url in urls:
        if not raw_url or not isinstance(raw_url, str):
            continue

        clean_url = raw_url.strip()
        try:
            parsed = urlparse(clean_url)
            host = (parsed.hostname or "").lower()
            path = parsed.path.strip("/")
        except Exception:
            continue

        if not path or path.lower() in IGNORED_PATHS:
            continue

        # Instagram
        if "instagram.com" in host:
            handle = path.split("/")[0].strip("@")
            if is_valid_social_handle(handle) and "instagram" not in socials:
                socials["instagram"] = f"https://www.instagram.com/{handle}"

        # Facebook
        elif "facebook.com" in host or "fb.com" in host:
            parts = [p for p in path.split("/") if p]
            if parts:
                first = parts[0]
                if first.lower() == "pages" and len(parts) >= 2:
                    handle = f"pages/{parts[1]}"
                else:
                    handle = first
                if is_valid_social_handle(handle) and "facebook" not in socials:
                    socials["facebook"] = f"https://www.facebook.com/{handle}"

        # LinkedIn
        elif "linkedin.com" in host:
            if "company/" in path or "school/" in path:
                company_slug = path.split("/")[1] if len(path.split("/")) > 1 else ""
                if is_valid_social_handle(company_slug) and "linkedin" not in socials:
                    socials["linkedin"] = f"https://www.linkedin.com/company/{company_slug}"

        # Twitter / X
        elif "twitter.com" in host or "x.com" in host:
            handle = path.split("/")[0].strip("@")
            if is_valid_social_handle(handle) and "x_url" not in socials:
                socials["x_url"] = f"https://x.com/{handle}"

        # TikTok
        elif "tiktok.com" in host:
            handle = path.split("/")[0].strip("@")
            if is_valid_social_handle(handle) and "tiktok" not in socials:
                socials["tiktok"] = f"https://www.tiktok.com/@{handle}"

        # YouTube
        elif "youtube.com" in host or "youtu.be" in host:
            if "@" in path or "channel/" in path or "c/" in path:
                channel = path.split("/")[1] if "/" in path else path.strip("@")
                if is_valid_social_handle(channel) and "youtube" not in socials:
                    socials["youtube"] = f"https://www.youtube.com/{path}"

    return socials


def extract_social_links(urls: List[str]) -> Dict[str, str]:
    """Use exact-domain profile normalization; share/post links are excluded."""
    from app.enrichment.social_intelligence import normalize_profile
    keys={'INSTAGRAM':'instagram','FACEBOOK':'facebook','LINKEDIN':'linkedin','X':'x_url','YOUTUBE':'youtube','TIKTOK':'tiktok','PINTEREST':'pinterest','THREADS':'threads'}
    result={}
    for value in urls:
        profile=normalize_profile(value)
        if profile and is_valid_social_handle(profile['handle']):
            result.setdefault(keys[profile['platform']],profile['profile_url'])
    return result
