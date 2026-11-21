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


def canonical_request(timestamp, nonce, method, path, body, actor, session_token='', client_id=''):
    parts=[timestamp, nonce, method, path, hashlib.sha256(body).hexdigest(), actor]
    if session_token:parts.append('session-sha256:'+hashlib.sha256(session_token.encode()).hexdigest())
    if client_id:parts.append('client:'+client_id)
    return "\n".join(parts)


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
    ORG_OPTIONAL_PREFIXES = ('/api/organization', '/api/profile', '/api/foundation/me','/api/billing','/api/help','/api/search')
    # Setup administration is available to verified active members before product
    # activation. Existing RBAC still controls every write; execution is excluded.
    SETUP_CONFIGURATION_PATHS = frozenset(('/api/settings','/api/workflow/defaults','/api/workflow/safety',
        '/api/automation/targets','/api/foundation/roles','/api/foundation/audit','/api/foundation/audit/export','/api/users','/api/email/gmail/authorize','/api/email/gmail/connect'))
    SETUP_REFERENCE_PATHS = frozenset(('/api/markets','/api/verticals','/api/foundation/countries','/api/foundation/locations','/api/email/gmail','/api/email/gmail/policy','/api/email/account'))

    async def authenticated(self,request,call_next):
        from app.api.read_cache import read_cache
        from app.api.permissions import begin_in
        from app.api import organization as org_context
        from fastapi import HTTPException
        from contextvars import copy_context
        import json
        mutation=request.method not in ('GET','HEAD','OPTIONS')
        raw=await request.body() if mutation else b''
        try:body=json.loads(raw) if raw else {}
        except ValueError:body={}
        if not isinstance(body,dict):body={}

        def prepare_entry():
            # One transaction/connection, with all original fresh membership,
            # RBAC, product and onboarding checks retained. Nothing is cached.
            from app.platform.modules import guard_route,guard_product_route
            from app.platform.context import workspace_scope
            with db_session() as c:
                if get_settings().heysow_accounts_enabled:
                    from app.accounts.policy import require_work_identity
                    require_work_identity(request.state.user_email)
                if get_settings().heysow_accounts_enabled and (request.state.user_email not in get_settings().allowed_emails or request.headers.get('x-le-session')):
                    from app.accounts.sessions import validate
                    validate(c,request.state.user_email,request.headers.get('x-le-session',''))
                state=org_context.resolve(c,request.state.user_email)
                request.state.organization=state
                request.state.organization_id=state['organization_id'] if state else None
                expected=request.query_params.get('expected_workspace')
                if expected is not None and expected!=request.state.organization_id:raise HTTPException(409,'Workspace changed. Reload this page before continuing.')
                request.state.role=None;request.state.audit_id=None
                if state is not None:
                    request.state.role,request.state.audit_id=begin_in(c,request.state.user_email,request.method,request.url.path,body,state['organization_id'])
                    if request.state.audit_id:c.commit() # Retain critical ATTEMPTED audit even when a later gate denies.
                guard_route(request.url.path,organization_id=request.state.organization_id,role=request.state.role,method=request.method,connection=c)
                setup=request.url.path in self.SETUP_CONFIGURATION_PATHS or request.method=='GET' and request.url.path in self.SETUP_REFERENCE_PATHS
                if not request.url.path.startswith(self.ORG_OPTIONAL_PREFIXES):
                    if state is None:raise HTTPException(403,{'detail':'Create your company to continue.','code':'ORGANIZATION_REQUIRED'})
                    if state['onboarding_status']!='COMPLETED' and not state.get('onboarding_deferred') and not setup:raise HTTPException(403,{'detail':'Finish company onboarding to continue.','code':'ONBOARDING_INCOMPLETE'})
                if state is None:return copy_context()
                if request.url.path not in self.SETUP_CONFIGURATION_PATHS and request.url.path not in self.SETUP_REFERENCE_PATHS:
                    guard_product_route(c,request.url.path,state['organization_id'])
                with workspace_scope(c,request.state.user_email,state['organization_id']):
                    # Context holds identity only, never an open connection or an
                    # authorization cache. It is copied into this request's task.
                    return copy_context()
        try:verified_context=await asyncio.to_thread(prepare_entry)
        except HTTPException as exc:
            return JSONResponse(exc.detail if isinstance(exc.detail,dict) else {'detail':exc.detail},status_code=exc.status_code)
        # Keep blocking database work off the event loop and release the pooled
        # connection before invoking handlers/providers. Python3.12 is pinned.
        return await asyncio.create_task(read_cache.handle(request,call_next),context=verified_context)
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
        if request.url.path in ('/api/billing/webhooks/creem','/api/billing/webhooks/creem/test') and request.method=='POST':return await call_next(request)
        if request.url.path=='/api/intent-radar/webhooks/github' and request.method=='POST':
            # GitHub App webhook uses its own bounded raw-body HMAC-SHA256 verification.
            return await call_next(request)
        if request.url.path=='/api/billing/payments/payu/callback' and request.method=='POST':return await call_next(request)
        if request.url.path=='/api/notifications/webhooks/resend' and request.method=='POST':return await call_next(request)
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
        from app.api.routes.accounts import PUBLIC,SESSION
        account_path=request.url.path in PUBLIC|SESSION
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > (8192 if account_path else 4_000_000 if request.url.path=='/api/experiments/catalog' else 1_048_576):
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
        account_bootstrap=settings.heysow_accounts_enabled and account_path and request.method=='POST'
        bootstrap=is_bootstrap(request.url.path,request.method) or account_bootstrap
        candidate=actor in settings.allowed_emails or bootstrap or settings.heysow_customer_access_enabled
        valid_fields = (timestamp.isdigit() and abs(time.time() - int(timestamp)) <= 60
                        and re.fullmatch(r"[a-zA-Z0-9-]{16,100}", nonce)
                        and candidate and 3<=len(actor)<=254 and actor == actor.lower()
                        and re.fullmatch(r"[a-f0-9]{64}", supplied))
        if not valid_fields:
            logger.warning("Internal request rejected: invalid authentication fields")
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        expected = hmac.new(settings.api_signing_secret.encode(), canonical_request(timestamp, nonce, request.method, path, body, actor, request.headers.get('x-le-session',''),request.headers.get('x-le-client','')).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            logger.warning("Internal request rejected: signature mismatch")
            return JSONResponse({"detail": "Invalid internal authentication."}, status_code=401)
        inserted=await asyncio.to_thread(claim_nonce,nonce)
        if inserted != 1:
            return JSONResponse({"detail": "Request has already been used."}, status_code=401)
        if actor not in settings.allowed_emails and not bootstrap:
            # Pool checkout and fresh admission reads may block. Never hold the
            # event loop while another request needs it to release a connection.
            def admitted():
                with db_session() as c:
                    return account_access(c,actor,require_terms=request.url.path!='/api/organization/admission/google')
            if not await asyncio.to_thread(admitted):return JSONResponse({'detail':'Account access is not enabled.'},status_code=401)
        request.state.user_email = actor
        request.state.internal_verified = True
        # Admission is an account-only broker operation, including renewed terms
        # for viewers. It cannot inherit the account's selected workspace scope.
        if account_bootstrap or request.url.path=='/api/organization/admission/google' and request.method=='POST':
            return await call_next(request)
        return await self.authenticated(request,call_next)


def actor(request):
    return request.state.user_email
