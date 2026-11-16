"""Fresh native admission must not stall unrelated requests under pool pressure."""
import asyncio,hashlib,hmac,threading,time
from contextlib import contextmanager
import pytest
from starlette.requests import Request
from starlette.responses import Response
from app.api.security import InternalAuthenticationMiddleware,canonical_request
from app.config.settings import get_settings

@pytest.mark.asyncio
@pytest.mark.parametrize('allowed',[True,False])
async def test_slow_native_admission_keeps_health_responsive_and_still_denies(monkeypatch,allowed):
    from app.api import security
    from app.platform import admission
    s=get_settings()
    monkeypatch.setattr(s,'app_env','production');monkeypatch.setattr(s,'allowed_user_emails','operator@example.com')
    monkeypatch.setattr(s,'heysow_customer_access_enabled',True)
    monkeypatch.setattr(s,'api_signing_secret','isolated-signing-secret-for-concurrency-test')
    entered=threading.Event();release=threading.Event()
    @contextmanager
    def session():yield object()
    def access(c,actor,**kwargs):
        assert actor=='fresh@example.com' and kwargs['require_terms']
        entered.set();release.wait(.8);return allowed
    monkeypatch.setattr(security,'db_session',session);monkeypatch.setattr(security,'claim_nonce',lambda nonce:1)
    monkeypatch.setattr(admission,'access',access)
    middleware=InternalAuthenticationMiddleware(lambda scope,receive,send:None)
    async def next_request(request):return Response(status_code=200)
    async def authenticated(request,call_next):
        assert request.state.user_email=='fresh@example.com' and request.state.internal_verified
        return await call_next(request)
    monkeypatch.setattr(middleware,'authenticated',authenticated)
    stamp=str(int(time.time()));nonce='isolated-concurrency-nonce-123';path='/api/organization/profile';actor='fresh@example.com'
    signature=hmac.new(s.api_signing_secret.encode(),canonical_request(stamp,nonce,'GET',path,b'',actor).encode(),hashlib.sha256).hexdigest()
    headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':signature}
    request=Request({'type':'http','method':'GET','path':path,'raw_path':path.encode(),'query_string':b'','headers':[(k.encode(),v.encode()) for k,v in headers.items()]})
    request._body=b''
    health=Request({'type':'http','method':'GET','path':'/api/health','headers':[]})
    started=time.monotonic();task=asyncio.create_task(middleware._dispatch(request,next_request))
    try:
        assert await asyncio.to_thread(entered.wait,1)
        assert (await middleware._dispatch(health,next_request)).status_code==200
        assert time.monotonic()-started<.4,'Admission blocked the event loop while waiting for database capacity'
    finally:release.set()
    assert (await task).status_code==(200 if allowed else 401)
