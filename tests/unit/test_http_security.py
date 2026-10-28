import httpx
import pytest
from app.utils.urls import is_safe_url
from app.utils.http import SafeAsyncClient
from app.utils.public_transport import PublicNetworkBackend
from unittest.mock import AsyncMock


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://169.254.169.254/computeMetadata/v1/", "http://[::1]/", "http://10.1.2.3/", "file:///etc/passwd", "https://user:password@public.example/", "http://public.example:8080/"])
def test_unsafe_destinations(url):
    assert not is_safe_url(url)


async def test_redirect_rejected_before_private_request(monkeypatch):
    requested = []
    monkeypatch.setattr("app.utils.http.is_safe_url", lambda url, check_dns: "127.0.0.1" not in url)
    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    async with SafeAsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError, match="Unsafe"):
            await client.get("https://public.example/")
    assert requested == ["https://public.example/"]


async def test_response_limit(monkeypatch):
    monkeypatch.setattr("app.utils.http.is_safe_url", lambda *a, **kw: True)
    async with SafeAsyncClient(max_bytes=4, transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"12345"))) as client:
        with pytest.raises(ValueError, match="byte limit"):
            await client.get("https://public.example/")


async def test_crawl_redirect_stays_on_host(monkeypatch):
    monkeypatch.setattr("app.utils.http.is_safe_url", lambda *a, **kw: True)
    async with SafeAsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "https://other.example/"}))) as client:
        with pytest.raises(ValueError, match="Cross-host"):
            await client.get("https://public.example/", allowed_host="public.example")


async def test_safe_redirect_preserves_headers_and_history(monkeypatch):
    monkeypatch.setattr("app.utils.http.is_safe_url", lambda *a, **kw: True)
    def respond(request):
        if request.url.path == "/":
            return httpx.Response(301, headers={"location": "/home"})
        return httpx.Response(200, headers={"content-type": "text/html", "strict-transport-security": "max-age=100"}, text="OK")
    async with SafeAsyncClient(transport=httpx.MockTransport(respond)) as client:
        response = await client.get("https://public.example/")
    assert response.text == "OK"
    assert len(response.history) == 1
    assert response.headers["strict-transport-security"] == "max-age=100"


@pytest.mark.parametrize('encoding',['gzip','deflate'])
async def test_compressed_response_is_decoded_once_with_decoded_byte_limit(monkeypatch,encoding):
    import gzip,zlib
    monkeypatch.setattr('app.utils.http.is_safe_url',lambda *a,**kw:True)
    payload=b'<html><title>Public business</title></html>'
    compressed=gzip.compress(payload) if encoding=='gzip' else zlib.compress(payload)
    transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-encoding':encoding,'content-length':str(len(compressed)),'strict-transport-security':'max-age=100'},content=compressed))
    async with SafeAsyncClient(transport=transport,max_bytes=100) as client:
        response=await client.get('https://public.example/')
        assert response.content==payload
        assert response.headers['content-length']==str(len(payload))
        assert 'content-encoding' not in response.headers
        assert response.headers['strict-transport-security']=='max-age=100'
    async with SafeAsyncClient(transport=transport,max_bytes=5) as client:
        with pytest.raises(ValueError,match='byte limit'):await client.get('https://public.example/')


async def test_dns_answers_are_checked_and_pinned(monkeypatch):
    backend = PublicNetworkBackend()
    backend.backend.connect_tcp = AsyncMock(return_value="stream")
    loop = __import__("asyncio").get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", AsyncMock(return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]))
    assert await backend.connect_tcp("public.example", 443) == "stream"
    assert backend.backend.connect_tcp.call_args.args[0] == "8.8.8.8"
    monkeypatch.setattr(loop, "getaddrinfo", AsyncMock(return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]))
    with pytest.raises(Exception, match="Non-public"):
        await backend.connect_tcp("rebound.example", 443)
