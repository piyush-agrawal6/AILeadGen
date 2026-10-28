"""Bounded HTTP fetches with TLS and validation before every redirect hop."""
from urllib.parse import urljoin, urlparse
import httpx
from app.utils.urls import is_safe_url
from app.utils.public_transport import PublicAsyncTransport


class SafeAsyncClient(httpx.AsyncClient):
    def __init__(self, *args, max_bytes=3_000_000, redirect_limit=5, **kwargs):
        kwargs.update(follow_redirects=False, verify=True, trust_env=False)
        if "transport" not in kwargs:
            kwargs["transport"] = PublicAsyncTransport()
        super().__init__(*args, **kwargs)
        self.max_bytes = max_bytes
        self.redirect_limit = redirect_limit

    async def get(self, url, *, allowed_host=None, **kwargs):
        history = []
        for _ in range(self.redirect_limit+1):
            if not is_safe_url(str(url), check_dns=True):
                raise ValueError("Unsafe HTTP destination")
            if allowed_host and urlparse(str(url)).hostname != allowed_host:
                raise ValueError("Cross-host crawl redirect blocked")
            request = self.build_request("GET", url, **kwargs)
            response = await self.send(request, stream=True, follow_redirects=False)
            try:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect missing destination")
                    url = urljoin(str(response.url), location)
                    history.append(httpx.Response(response.status_code, headers=response.headers, request=request))
                    continue
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > self.max_bytes:
                        raise ValueError("Response exceeds configured byte limit")
                # aiter_bytes already decodes Content-Encoding. Keeping that
                # header would make the reconstructed response decode twice.
                headers=httpx.Headers(response.headers)
                headers.pop('content-encoding',None)
                headers.pop('content-length',None)
                return httpx.Response(response.status_code, headers=headers, content=bytes(body), request=request, history=history)
            finally:
                await response.aclose()
        raise ValueError("Redirect limit exceeded")
