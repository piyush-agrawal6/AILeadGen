import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse
import tldextract

# Prohibited schemes
PROHIBITED_SCHEMES = {"file", "javascript", "data", "vbscript", "about"}

# Reserved / Private IP networks for SSRF protection
PRIVATE_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Common tracking parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "mc_cid", "mc_eid"
}

_tld_extractor = tldextract.TLDExtract()


def is_safe_ip(ip_str: str) -> bool:
    """Check if an IP string is not in private, reserved, or loopback ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
        for net in PRIVATE_NETWORKS:
            if ip in net:
                return False
        return True
    except ValueError:
        return False


def is_safe_url(url: str, check_dns: bool = False) -> bool:
    """Validate that a URL is well-formed, uses http/https, and does not target internal assets."""
    if not url or not isinstance(url, str):
        return False

    url_str = url.strip()
    if not url_str:
        return False

    # Check for prohibited schemes or javascript prefix
    lower_url = url_str.lower()
    for scheme in PROHIBITED_SCHEMES:
        if lower_url.startswith(f"{scheme}:"):
            return False

    try:
        parsed = urlparse(url_str)
    except Exception:
        return False

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254"):
        return False

    if hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False

    # If it's a literal IP
    try:
        ip = ipaddress.ip_address(hostname)
        return is_safe_ip(str(ip))
    except ValueError:
        pass

    if check_dns:
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for item in resolved_ips:
                ip_addr = item[4][0]
                if not is_safe_ip(ip_addr):
                    return False
        except Exception:
            return False

    return True


def sanitize_url(url: str) -> str:
    """Clean and normalize a website URL."""
    if not url or not isinstance(url, str):
        return ""

    url_str = url.strip()
    if not url_str:
        return ""

    # Prepend http:// if missing scheme
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_str):
        url_str = "http://" + url_str

    try:
        parsed = urlparse(url_str)
    except Exception:
        return ""

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return ""

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ""

    # Remove default port
    port = parsed.port
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"

    # Clean path
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Strip fragments
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def extract_domain(url: str) -> str:
    """Extract registered apex domain (e.g. example.com) from URL or domain string."""
    if not url:
        return ""

    url_str = url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_str):
        url_str = "http://" + url_str

    try:
        extracted = _tld_extractor(url_str)
        if extracted.domain and extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}".lower()
        if extracted.domain:
            return extracted.domain.lower()
    except Exception:
        pass

    try:
        parsed = urlparse(url_str)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def extract_hostname(url: str) -> str:
    """Extract normalized lowercase hostname from URL."""
    if not url:
        return ""
    url_str = url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_str):
        url_str = "http://" + url_str
    try:
        parsed = urlparse(url_str)
        return (parsed.hostname or "").lower()
    except Exception:
        return ""
