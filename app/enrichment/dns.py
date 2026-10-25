import logging
import re
from typing import Dict, Tuple
import dns.resolver

logger = logging.getLogger("leadengine.enrichment.dns")

# Simple email regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# In-memory domain MX cache
_MX_CACHE: Dict[str, Tuple[str, bool]] = {}


def validate_email_syntax(email: str) -> bool:
    """Validate RFC 5322 basic syntax."""
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def check_email_dns(email: str, timeout: float = 4.0) -> Tuple[str, bool]:
    """Validate email syntax and check DNS MX records for domain.
    
    Returns:
        (status_string, is_valid_boolean)
        Statuses: VALID_DOMAIN, NO_MX, INVALID_SYNTAX, UNKNOWN
    """
    if not email or not isinstance(email, str):
        return "INVALID_SYNTAX", False

    clean_email = email.strip().lower()
    if not validate_email_syntax(clean_email):
        return "INVALID_SYNTAX", False

    domain = clean_email.split("@")[1].strip()
    if not domain or "." not in domain:
        return "INVALID_SYNTAX", False

    if domain in _MX_CACHE:
        return _MX_CACHE[domain]

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    try:
        answers = resolver.resolve(domain, "MX")
        if answers and len(answers) > 0:
            result = ("VALID_DOMAIN", True)
            _MX_CACHE[domain] = result
            return result
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        # Fallback: check if domain has an A record (some servers receive mail directly on A record)
        try:
            a_answers = resolver.resolve(domain, "A")
            if a_answers and len(a_answers) > 0:
                result = ("VALID_DOMAIN", True)
                _MX_CACHE[domain] = result
                return result
        except Exception:
            pass
        result = ("NO_MX", False)
        _MX_CACHE[domain] = result
        return result
    except dns.resolver.Timeout:
        result = ("UNKNOWN", False)
        return result
    except Exception as e:
        logger.debug(f"DNS lookup error for {domain}: {e}")
        result = ("UNKNOWN", False)
        return result

    result = ("NO_MX", False)
    _MX_CACHE[domain] = result
    return result
