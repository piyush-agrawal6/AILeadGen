import re
from typing import Dict, List, Set
from bs4 import BeautifulSoup

# Signatures for technology detection
TECH_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "WordPress": {
        "generator": ["wordpress"],
        "scripts": ["wp-content", "wp-includes", "wp-json"],
        "html": ["/wp-content/", "wp-block-", "class=\"wp-"],
    },
    "Elementor": {
        "generator": ["elementor"],
        "scripts": ["elementor"],
        "html": ["elementor-widget", "elementor-default", "elementor-", "class=\"elementor"],
    },
    "WooCommerce": {
        "generator": ["woocommerce"],
        "scripts": ["woocommerce"],
        "html": ["woocommerce-price-amount", "woocommerce-product"],
    },
    "Wix": {
        "generator": ["wix"],
        "scripts": ["static.parastorage.com", "wix.com"],
        "html": ["wix-image", "wix-site", "wixui"],
    },
    "Squarespace": {
        "generator": ["squarespace"],
        "scripts": ["squarespace.com", "sqsp.net"],
        "html": ["squarespace-config", "class=\"sqs-"],
    },
    "Shopify": {
        "generator": ["shopify"],
        "scripts": ["cdn.shopify.com", "shopify.com"],
        "html": ["shopify-section", "class=\"shopify"],
    },
    "Webflow": {
        "generator": ["webflow"],
        "scripts": ["webflow.com", "assets.website-files.com"],
        "html": ["html data-wf-page", "class=\"w-"],
    },
    "Next.js": {
        "generator": ["next.js"],
        "scripts": ["/_next/static/", "/_next/"],
        "html": ["id=\"__next\"", "__NEXT_DATA__"],
    },
    "React": {
        "generator": [],
        "scripts": ["react.production.min.js", "react-dom"],
        "html": ["data-reactroot", "data-reactid"],
    },
    "Vue": {
        "generator": [],
        "scripts": ["vue.min.js", "vue.runtime"],
        "html": ["data-v-", "data-vue"],
    },
    "Angular": {
        "generator": [],
        "scripts": ["angular.min.js", "angular.js"],
        "html": ["ng-app", "ng-controller", "ng-version"],
    },
    "jQuery": {
        "generator": [],
        "scripts": ["jquery.min.js", "jquery-", "code.jquery.com"],
        "html": [],
    },
    "Bootstrap": {
        "generator": [],
        "scripts": ["bootstrap.min.js", "bootstrap.bundle"],
        "html": ["class=\"container-fluid\"", "class=\"btn btn-", "class=\"col-md-"],
    },
    "Cloudflare": {
        "generator": [],
        "scripts": ["cdnjs.cloudflare.com", "challenges.cloudflare.com", "email-decode.min.js"],
        "html": ["cf-browser-verification"],
    },
}

ANALYTICS_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "Google Analytics": {
        "scripts": ["google-analytics.com/analytics.js", "gtag/js", "gtag("],
        "html": ["gtag('config', 'G-", "ga('create', 'UA-"],
    },
    "Google Tag Manager": {
        "scripts": ["googletagmanager.com/gtm.js"],
        "html": ["googletagmanager.com/ns.html", "gtm.start"],
    },
    "Meta Pixel": {
        "scripts": ["connect.facebook.net/en_US/fbevents.js", "fbq("],
        "html": ["fbq('init'", "facebook.com/tr?id="],
    },
    "Microsoft Clarity": {
        "scripts": ["clarity.ms/tag/"],
        "html": ["clarity(\"set\""],
    },
    "Plausible": {
        "scripts": ["plausible.io/js/script.js", "plausible.io"],
        "html": ["data-domain="],
    },
    "PostHog": {
        "scripts": ["posthog.com", "app.posthog.com"],
        "html": ["posthog.init"],
    },
}


def detect_technologies(html: str, headers: Dict[str, str] = None) -> List[str]:
    """Detect technologies and frameworks from HTML source and headers."""
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    detected: Set[str] = set()

    # 1. Meta generator tag
    generator_meta = soup.find("meta", attrs={"name": re.compile(r"^generator$", re.I)})
    generator_content = (generator_meta.get("content") or "").lower() if generator_meta else ""

    # 2. Script source attributes
    scripts = [s.get("src", "").lower() for s in soup.find_all("script") if s.get("src")]
    script_texts = [s.get_text().lower() for s in soup.find_all("script") if not s.get("src")]
    all_script_text = " ".join(script_texts)

    lower_html = html.lower()

    # Check headers
    if headers:
        server = headers.get("server", "").lower()
        if "cloudflare" in server:
            detected.add("Cloudflare")
        if "nginx" in server:
            detected.add("Nginx")
        if "apache" in server:
            detected.add("Apache")

    # Match Tech Signatures
    for tech, sigs in TECH_SIGNATURES.items():
        # Check generator
        if any(g in generator_content for g in sigs["generator"]):
            detected.add(tech)
            continue
        # Check script sources
        if any(any(s_pattern in src for s_pattern in sigs["scripts"]) for src in scripts):
            detected.add(tech)
            continue
        # Check html snippets
        if any(h_pattern.lower() in lower_html for h_pattern in sigs["html"]):
            detected.add(tech)

    return sorted(list(detected))


def detect_analytics(html: str) -> List[str]:
    """Detect presence of analytics platforms in HTML."""
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    detected: Set[str] = set()

    scripts = [s.get("src", "").lower() for s in soup.find_all("script") if s.get("src")]
    script_texts = [s.get_text().lower() for s in soup.find_all("script") if not s.get("src")]
    all_script_content = " ".join(script_texts)
    lower_html = html.lower()

    for provider, sigs in ANALYTICS_SIGNATURES.items():
        # Check external scripts
        if any(any(pat in src for pat in sigs["scripts"]) for src in scripts):
            detected.add(provider)
            continue
        # Check inline scripts & html
        if any(pat.lower() in all_script_content or pat.lower() in lower_html for pat in sigs["scripts"] + sigs["html"]):
            detected.add(provider)

    return sorted(list(detected))
