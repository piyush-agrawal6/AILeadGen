"""HTTPX transport that connects only to validated, pinned public IP addresses.

TLS still uses the original hostname for certificate verification/SNI. Built on
HTTPX's public transport API and HTTPCore's public network-backend interface.
"""
import asyncio
import socket
import ssl
import httpcore
import httpx
from app.utils.urls import is_safe_ip


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self):
        self.backend = httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if port not in (80, 443):
            raise httpcore.ConnectError("Non-web port blocked")
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=timeout or 5,
        )
        ips = list(dict.fromkeys(item[4][0] for item in addresses))
        if not ips or any(not is_safe_ip(ip) for ip in ips):
            raise httpcore.ConnectError("Non-public DNS destination blocked")
        # No second hostname lookup: connect to the validated literal address.
        return await self.backend.connect_tcp(ips[0], port, timeout, local_address, socket_options)

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Unix sockets are forbidden")

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        async for chunk in self.stream:
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class PublicAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(), network_backend=PublicNetworkBackend(),
            max_connections=20, max_keepalive_connections=10, retries=0,
        )

    async def handle_async_request(self, request):
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(scheme=request.url.raw_scheme, host=request.url.raw_host, port=request.url.port, target=request.url.raw_path),
            headers=request.headers.raw, content=request.stream, extensions=request.extensions,
        )
        try:
            response = await self.pool.handle_async_request(core_request)
        except (httpcore.ConnectError, httpcore.TimeoutException, asyncio.TimeoutError) as exc:
            raise httpx.ConnectError("Public website connection failed", request=request) from exc
        return httpx.Response(response.status, headers=response.headers, stream=_ResponseStream(response.stream), extensions=response.extensions)

    async def aclose(self):
        await self.pool.aclose()
