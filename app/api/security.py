"""Server-to-server authentication. Browser credentials are never trusted here."""
import hashlib
import hmac
import re
import time
import asyncio
import threading
import logging
from contextlib import ExitStack
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.settings import get_settings
from app.database.connection import db_session

logger = logging.getLogger(__name__)


def canonical_request(timestamp, nonce, method, path, body, actor):
    return "\n".join([timestamp, nonce, method, path, hashlib.sha256(body).hexdigest(), actor])


_nonce_cleanup_lock=threading.Lock()
_next_nonce_cleanup=0.0

def claim_nonce(nonce):
    global _next_nonce_cleanup
    with db_session() as conn:
        # Unique nonce insertion still happens on every authenticated request.
        # Expired-row maintenance needs no per-page table rewrite.
        with _nonce_cleanup_lock:
            if time.monotonic()>=_next_nonce_cleanup:
                conn.execute("DELETE FROM internal_request_nonces WHERE expires_at < ?", (int(time.time()),))
                _next_nonce_cleanup=time.monotonic()+30
        return conn.execute("INSERT INTO internal_request_nonces(nonce,expires_at) VALUES(?,?) ON CONFLICT(nonce) DO NOTHING", (nonce, int(time.time()) + 120)).rowcount


class InternalAuthenticationMiddleware(BaseHTTPMiddleware):
    # Paths that must work before an organization exists (onboarding, personal
    # profile, identity). Everything else requires completed company onboarding.
    ORG_OPTIONAL_PREFIXES = ('/api/organization', '/api/profile', '/api/foundation/me')
    # Setup administration is available to verified active members before product
    # activation. Existing RBAC still controls every write; execution is excluded.
    SETUP_CONFIGURATION_PATHS = frozenset(('/api/settings','/api/workflow/defaults','/api/workflow/safety',
        '/api/automation/targets','/api/foundation/roles','/api/foundation/audit','/api/users','/api/email/gmail/authorize','/api/email/gmail/connect'))
    SETUP_REFERENCE_PATHS = frozenset(('/api/markets','/api/verticals','/api/foundation/countries','/api/foundation/locations','/api/email/gmail','/api/email/gmail/policy','/api/email/account'))

    async def authenticated(self,request,call_next):
        from app.api.read_cache import read_cache
        from app.api.permissions import begin
        from app.api import organization as org_context
        from fastapi import HTTPException
        import json
        from app.database.connection import db_session
        # The primary owner is already established by signed authentication.
        # Other roles are rechecked before every read, including cache hits.
        settings=get_settings();owner=settings.allowed_emails[0] if settings.allowed_emails else None
        mutation=request.method not in ('GET','HEAD','OPTIONS')
        # Organization context: membership identifies the tenant, never the browser.
        def resolve_organization():
            with db_session() as c:
                state=org_context.resolve(c,request.state.user_email)
                return state
        state=await asyncio.to_thread(resolve_organization)
        request.state.organization=state
        request.state.organization_id=state['organization_id'] if state else None
        audit_id=None
        if state is not None:
            raw=await request.body() if mutation else b''
            try:body=json.loads(raw) if raw else {}
            except ValueError:body={}
            if not isinstance(body,dict):body={}
            try:request.state.role,audit_id=await asyncio.to_thread(begin,request.state.user_email,request.method,request.url.path,body,request.state.organization_id)
            except HTTPException as exc:return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        else:request.state.role=None
        request.state.audit_id=audit_id
        from app.platform.modules import guard_route
        try:guard_route(request.url.path,organization_id=request.state.organization_id,role=request.state.role,method=request.method)
        except HTTPException as exc:return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        if not request.url.path.startswith(self.ORG_OPTIONAL_PREFIXES):
            if state is None:
                return JSONResponse({'detail':'Create your company to continue.','code':'ORGANIZATION_REQUIRED'},status_code=403)
            setup_path=request.url.path in self.SETUP_CONFIGURATION_PATHS or request.method=='GET' and request.url.path in self.SETUP_REFERENCE_PATHS
            if state['onboarding_status']!='COMPLETED' and not setup_path:
                return JSONResponse({'detail':'Finish company onboarding to continue.','code':'ONBOARDING_INCOMPLETE'},status_code=403)
        if state is None:
            return await read_cache.handle(request,call_next)
        from app.platform.context import workspace_scope
        with ExitStack() as scopes:
            with db_session() as c:
                if request.url.path not in self.SETUP_CONFIGURATION_PATHS and request.url.path not in self.SETUP_REFERENCE_PATHS:
                    from app.platform.modules import guard_product_route
                    try:guard_product_route(c,request.url.path,state['organization_id'])
                    except HTTPException as exc:return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
                scopes.enter_context(workspace_scope(c,request.state.user_email,state['organization_id']))
            # Verification is complete; retain the trusted context, not an idle
            # pooled connection, while handlers obtain their own connections.
            response=await read_cache.handle(request,call_next)
        return response
    async def dispatch(self,request,call_next):
        from app.platform import request_metrics
        started=time.monotonic();token=request_metrics.begin()
        try:
            response=await self._dispatch(request,call_next)
            if getattr(request.state,'user_email',None):
                previous=response.headers.get('Server-Timing','')
                response.headers['Server-Timing']=', '.join(filter(None,(previous,request_metrics.header(),f'app;dur={(time.monotonic()-started)*1000:.1f}')))
            return response
        finally:request_metrics.finish(token)

    async def _dispatch(self, request, call_next):
        if request.url.path=='/api/billing/webhooks/razorpay' and request.method=='POST':
            # This one provider callback uses its own bounded raw-body HMAC;
            # arbitrary billing/API prefixes never bypass signed authentication.
            return await call_next(request)
        if request.url.path == "/api/health" or re.fullmatch(r"/api/tracking/(?:o|c|u)/[A-Za-z0-9_.-]{1,100}", request.url.path):
            return await call_next(request)
        if request.url.path.startswith('/api/v1/'):
            from app.developer.keys import handle
            return await handle(request,call_next)
        settings = get_settings()
        if settings.app_env == "test" or (settings.app_env != "production" and settings.auth_disabled_local):
            test_actor = request.headers.get("x-le-user", "") if settings.app_env == "test" else ""
            request.state.user_email = test_actor if test_actor in settings.allowed_emails else settings.allowed_emails[0] if settings.allowed_emails else "local@localhost"
            return await self.authenticated(request,call_next)
        if not settings.api_signing_secret:
            return JSONResponse({"detail": "API authentication is not configured."}, status_code=503)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > (4_000_000 if request.url.path=='/api/experiments/catalog' else 1_048_576):
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
        from app.platform.admission import is_bootstrap,access as account_access
        bootstrap=is_bootstrap(request.url.path,request.method)
        candidate=actor in settings.allowed_emails or bootstrap or settings.heysow_customer_access_enabled
        valid_fields = (timestamp.isdigit() and abs(time.time() - int(timestamp)) <= 60
                        and re.fullmatch(r"[a-zA-Z0-9-]{16,100}", nonce)
                        and candidate and 3<=len(actor)<=254 and actor == actor.lower()
                        and re.fullmatch(r"[a-f0-9]{64}", supplied))
        if not valid_fields:
            logger.warning("Internal request rejected: invalid authentication fields")
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        expected = hmac.new(settings.api_signing_secret.encode(), canonical_request(timestamp, nonce, request.method, path, body, actor).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            logger.warning("Internal request rejected: signature mismatch")
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        inserted=await asyncio.to_thread(claim_nonce,nonce)
        if inserted != 1:
            return JSONResponse({"detail": "Request has already been used."}, status_code=401)
        if actor not in settings.allowed_emails and not bootstrap:
            with db_session() as c:
                if not account_access(c,actor,require_terms=request.url.path!='/api/organization/admission/google'):return JSONResponse({'detail':'Account access is not enabled.'},status_code=401)
        request.state.user_email = actor
        request.state.internal_verified = True
        # Admission is an account-only broker operation, including renewed terms
        # for viewers. It cannot inherit the account's selected workspace scope.
        if request.url.path=='/api/organization/admission/google' and request.method=='POST':
            return await call_next(request)
        return await self.authenticated(request,call_next)


def actor(request):
    return request.state.user_email
