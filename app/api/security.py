"""Server-to-server authentication. Browser credentials are never trusted here."""
import hashlib
import hmac
import re
import time
import asyncio
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.settings import get_settings
from app.database.connection import db_session


def canonical_request(timestamp, nonce, method, path, body, actor):
    return "\n".join([timestamp, nonce, method, path, hashlib.sha256(body).hexdigest(), actor])


def claim_nonce(nonce):
    with db_session() as conn:
        conn.execute("DELETE FROM internal_request_nonces WHERE expires_at < ?", (int(time.time()),))
        return conn.execute("INSERT INTO internal_request_nonces(nonce,expires_at) VALUES(?,?) ON CONFLICT(nonce) DO NOTHING", (nonce, int(time.time()) + 120)).rowcount


class InternalAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/api/health" or re.fullmatch(r"/api/tracking/(?:o|c|u)/[A-Za-z0-9_.-]{1,100}", request.url.path):
            return await call_next(request)
        settings = get_settings()
        if settings.app_env == "test" or (settings.app_env != "production" and settings.auth_disabled_local):
            test_actor = request.headers.get("x-le-user", "") if settings.app_env == "test" else ""
            request.state.user_email = test_actor if test_actor in settings.allowed_emails else settings.allowed_emails[0] if settings.allowed_emails else "local@localhost"
            return await call_next(request)
        if not settings.api_signing_secret:
            return JSONResponse({"detail": "API authentication is not configured."}, status_code=503)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1_048_576:
                return JSONResponse({"detail": "Request too large."}, status_code=413)
        # Cache the bounded body for downstream Pydantic parsing.
        request._body = bytes(body)
        timestamp = request.headers.get("x-le-timestamp", "")
        nonce = request.headers.get("x-le-nonce", "")
        actor = request.headers.get("x-le-user", "")
        supplied = request.headers.get("x-le-signature", "")
        path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
        query = request.scope.get("query_string", b"").decode("ascii")
        if query:
            path += "?" + query
        valid_fields = (timestamp.isdigit() and abs(time.time() - int(timestamp)) <= 60
                        and re.fullmatch(r"[a-zA-Z0-9-]{16,100}", nonce)
                        and actor in settings.allowed_emails and actor == actor.lower()
                        and re.fullmatch(r"[a-f0-9]{64}", supplied))
        if not valid_fields:
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        expected = hmac.new(settings.api_signing_secret.encode(), canonical_request(timestamp, nonce, request.method, path, body, actor).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        inserted=await asyncio.to_thread(claim_nonce,nonce)
        if inserted != 1:
            return JSONResponse({"detail": "Request has already been used."}, status_code=401)
        request.state.user_email = actor
        return await call_next(request)


def actor(request):
    return request.state.user_email
