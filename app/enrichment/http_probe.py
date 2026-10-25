import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel

from app.config.settings import get_settings
from app.utils.urls import is_safe_url, sanitize_url

logger = logging.getLogger("leadengine.enrichment.http_probe")


class ProbeResult(BaseModel):
    requested_url: str
    final_url: Optional[str] = None
    reachable: bool = False
    http_status: Optional[int] = None
    https_enabled: bool = False
    redirect_count: int = 0
    content_type: Optional[str] = None
    html_content: Optional[str] = None
    error: Optional[str] = None


async def probe_website(
    url: str,
    timeout_seconds: float = 10.0,
    max_response_bytes: int = 3_000_000,
) -> ProbeResult:
    """Probe a website URL with cheap HTTP request, handle redirects, verify reachability and SSRF safety."""
    clean_url = sanitize_url(url)
    if not clean_url or not is_safe_url(clean_url):
        return ProbeResult(
            requested_url=url,
            reachable=False,
            error="INVALID_OR_UNSAFE_URL",
        )

    settings = get_settings()
    headers = {
        "User-Agent": settings.crawler_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Attempt HTTPS first if URL starts with http://
    targets_to_try = []
    if clean_url.startswith("http://"):
        targets_to_try.append("https://" + clean_url[7:])
        targets_to_try.append(clean_url)
    else:
        targets_to_try.append(clean_url)
        # Fallback to http if https fails
        targets_to_try.append("http://" + clean_url[8:])

    last_error = None
    for target in targets_to_try:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_seconds, connect=5.0),
                follow_redirects=True,
                max_redirects=5,
                verify=False,  # Still check https_enabled based on scheme
            ) as client:
                resp = await client.get(target, headers=headers)
                
                final_url = str(resp.url)
                if not is_safe_url(final_url):
                    return ProbeResult(
                        requested_url=url,
                        reachable=False,
                        error="SSRF_REDIRECT_DETECTED",
                    )

                content_type = resp.headers.get("content-type", "").lower()
                is_html = "text/html" in content_type or "application/xhtml" in content_type or not content_type

                html_text = ""
                if is_html:
                    # Limit body read
                    content_bytes = resp.content[:max_response_bytes]
                    html_text = content_bytes.decode("utf-8", errors="replace")

                is_https = final_url.startswith("https://")
                redirect_count = len(resp.history)

                reachable = resp.status_code < 400

                return ProbeResult(
                    requested_url=url,
                    final_url=final_url,
                    reachable=reachable,
                    http_status=resp.status_code,
                    https_enabled=is_https,
                    redirect_count=redirect_count,
                    content_type=content_type,
                    html_content=html_text if reachable else None,
                    error=None if reachable else f"HTTP_{resp.status_code}",
                )
        except httpx.ConnectTimeout:
            last_error = "CONNECT_TIMEOUT"
        except httpx.ReadTimeout:
            last_error = "READ_TIMEOUT"
        except httpx.ConnectError:
            last_error = "CONNECT_ERROR"
        except Exception as e:
            last_error = f"PROBE_FAILED: {str(e)[:50]}"

    return ProbeResult(
        requested_url=url,
        reachable=False,
        error=last_error or "SITE_UNREACHABLE",
    )
