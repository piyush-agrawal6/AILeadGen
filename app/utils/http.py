"""Bounded HTTP fetches with TLS and validation before every redirect hop."""
from urllib.parse import urljoin, urlparse
import asyncio
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

    async def get(self, url, *, allowed_host=None, allowed_domain=None, require_https=False,before_request=None, **kwargs):
        history = []
        for _ in range(self.redirect_limit+1):
            if require_https and urlparse(str(url)).scheme!='https':raise ValueError('HTTPS is required for public business research')
            try:safe=await asyncio.wait_for(asyncio.to_thread(is_safe_url,str(url),check_dns=True),timeout=5)
            except asyncio.TimeoutError:raise ValueError('Destination validation timed out') from None
            if not safe:
                raise ValueError("Unsafe HTTP destination")
            if allowed_host and urlparse(str(url)).hostname != allowed_host:
                raise ValueError("Cross-host crawl redirect blocked")
            if allowed_domain:
                from app.utils.urls import _tld_extractor
                if _tld_extractor(urlparse(str(url)).hostname or '').top_domain_under_public_suffix != allowed_domain:
                    raise ValueError('Cross-domain crawl redirect blocked')
            if before_request is not None:await before_request(str(url))
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
