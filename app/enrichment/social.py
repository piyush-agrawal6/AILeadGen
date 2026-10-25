import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Generic platform roots and non-profile paths to ignore
IGNORED_PATHS = {
    "", "/", "share", "sharer", "intent", "home", "login", "signup", "search",
    "pages", "p", "reel", "stories", "hashtag", "explore", "about", "help",
    "privacy", "terms", "policies", "groups", "watch"
}


def extract_social_links(urls: List[str]) -> Dict[str, str]:
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
            if handle and handle.lower() not in IGNORED_PATHS and "instagram" not in socials:
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
                if handle.lower() not in IGNORED_PATHS and "facebook" not in socials:
                    socials["facebook"] = f"https://www.facebook.com/{handle}"

        # LinkedIn
        elif "linkedin.com" in host:
            if "company/" in path or "school/" in path:
                if "linkedin" not in socials:
                    socials["linkedin"] = f"https://www.linkedin.com/{path}"

        # Twitter / X
        elif "twitter.com" in host or "x.com" in host:
            handle = path.split("/")[0].strip("@")
            if handle and handle.lower() not in IGNORED_PATHS and "x_url" not in socials:
                socials["x_url"] = f"https://x.com/{handle}"

        # TikTok
        elif "tiktok.com" in host:
            if "@" in path and "tiktok" not in socials:
                handle = path.split("/")[0]
                socials["tiktok"] = f"https://www.tiktok.com/{handle}"

        # YouTube
        elif "youtube.com" in host or "youtu.be" in host:
            if ("@" in path or "channel/" in path or "c/" in path) and "youtube" not in socials:
                socials["youtube"] = f"https://www.youtube.com/{path}"

    return socials
