import hashlib
import hmac
import time
import uuid
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from app.api.server import create_app
from app.api.security import canonical_request
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations


@pytest.fixture
def secured(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "auth_disabled_local", False)
    monkeypatch.setattr(settings, "upstash_redis_rest_url", "")
    monkeypatch.setattr(settings, "upstash_redis_rest_token", "")
    monkeypatch.setattr(settings, "api_signing_secret", "s" * 32)
    monkeypatch.setattr(settings, "allowed_user_emails", "founder@example.com")
    db_path = tmp_path / "auth.db"
    monkeypatch.setattr(settings,"database_path",str(db_path))
    db = get_connection(db_path)
    run_migrations(db)
    db.close()
    @contextmanager
    def session():
        db = get_connection(db_path)
        try:
            yield db
            db.commit()
        finally:
            db.close()
    monkeypatch.setattr("app.api.security.db_session", session)
    yield TestClient(create_app()), settings


def signed(settings, method="GET", path="/api/verticals", body=b"", timestamp=None, actor="founder@example.com"):
    timestamp = str(timestamp or int(time.time()))
    nonce = str(uuid.uuid4())
    signature = hmac.new(settings.api_signing_secret.encode(), canonical_request(timestamp, nonce, method, path, body, actor).encode(), hashlib.sha256).hexdigest()
    return {"x-le-timestamp": timestamp, "x-le-nonce": nonce, "x-le-user": actor, "x-le-signature": signature}


def test_unauthenticated_read_and_privileged_write_denied(secured):
    client, _ = secured
    assert client.get("/api/verticals").status_code == 401
    assert client.post("/api/scans", json={"market": "Austin"}).status_code == 401
    assert client.get("/api/client-reports/unknown/download").status_code == 401
    assert client.post("/api/leads/1/pdf-reports").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_valid_request_and_persistent_replay_rejection(secured):
    client, settings = secured
    headers = signed(settings)
    assert client.get("/api/verticals", headers=headers).status_code == 200
    assert client.get("/api/verticals", headers=headers).status_code == 401


def test_expired_signature_denied(secured):
    client, settings = secured
    assert client.get("/api/verticals", headers=signed(settings, timestamp=int(time.time())-120)).status_code == 401


def test_invalid_signature_denied(secured):
    client, settings = secured
    headers = signed(settings)
    headers["x-le-signature"] = "0" * 64
    assert client.get("/api/verticals", headers=headers).status_code == 401


def test_literal_secret_preserved_and_rejection_diagnostics_redacted(secured, caplog):
    client, settings = secured
    settings.api_signing_secret = "controlled-$literal-${never_expand}-signing-secret"
    assert client.get("/api/verticals", headers=signed(settings)).status_code == 200
    headers = signed(settings)
    headers["x-le-signature"] = "0" * 64
    assert client.get("/api/verticals", headers=headers).status_code == 401
    assert "signature mismatch" in caplog.text
    assert settings.api_signing_secret not in caplog.text
    assert headers["x-le-user"] not in caplog.text
    assert headers["x-le-signature"] not in caplog.text


def test_non_allowlisted_actor_denied(secured):
    client, settings = secured
    assert client.get("/api/verticals", headers=signed(settings, actor="stranger@example.com")).status_code == 401


def test_signature_binds_query_and_body(secured):
    client, settings = secured
    headers = signed(settings)
    assert client.get("/api/verticals?extra=1", headers=headers).status_code == 401
    headers = signed(settings, method="POST", path="/api/scans", body=b"{}")
    assert client.post("/api/scans", content=b'{"tampered":true}', headers=headers).status_code == 401


def test_request_body_bounded_before_parsing(secured):
    client, _ = secured
    assert client.post("/api/scans", content=b"x" * 1_048_577).status_code == 413


def test_workspace_verification_releases_connection_before_handler(secured,monkeypatch):
    from app.database import connection
    from app.platform.context import current
    client,settings=secured;original=connection.db_session;active={'count':0}
    @contextmanager
    def tracked(*args,**kwargs):
        with original(*args,**kwargs) as c:
            active['count']+=1
            try:yield c
            finally:active['count']-=1
    monkeypatch.setattr(connection,'db_session',tracked)
    path='/api/organization/connection-probe'
    @client.app.get(path)
    def probe():
        assert active['count']==0, 'Middleware must not reserve a pool slot throughout the downstream request.'
        assert current().actor=='founder@example.com'
        return {'verified':bool(current().organization_id)}
    response=client.get(path,headers=signed(settings,path=path))
    assert response.status_code==200 and response.json()['verified']

def test_fresh_authorization_context_crosses_async_tasks_and_thread_without_extra_sessions(secured,monkeypatch):
    import asyncio
    from app.api import security
    from app.platform.context import current
    client,settings=secured;entered=[];original=security.db_session
    @contextmanager
    def counted():
        entered.append(True)
        with original() as c:yield c
    monkeypatch.setattr(security,'db_session',counted)
    async def probe():
        direct=current()
        threaded=await asyncio.to_thread(current)
        async def child():return current()
        nested=await asyncio.create_task(child())
        assert direct==threaded==nested
        return {'actor':direct.actor,'organization_id':direct.organization_id}
    path='/api/organization/current-context-probe';client.app.add_api_route(path,probe,methods=['GET'])
    response=client.get(path,headers=signed(settings,path=path))
    assert response.status_code==200 and response.json()['actor']=='founder@example.com'
    assert len(entered)==2 # Durable nonce + one complete fresh authorization transaction.
    with original() as c:c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=?",('founder@example.com',))
    assert client.get(path,headers=signed(settings,path=path)).status_code in (401,403)
