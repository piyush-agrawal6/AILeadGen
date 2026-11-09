import uuid
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.config.settings import get_settings
from app.api.server import create_app
from app.api.services.scan_manager import scan_manager
from app.pipeline.fixtures import run_fixture


@pytest.fixture
def client(tmp_path,monkeypatch,request):
    settings=get_settings()
    monkeypatch.setattr(settings,"database_path",str(tmp_path/"campaigns.db"))
    monkeypatch.setattr(settings,"allowed_user_emails","a@example.com,b@example.com")
    executor=AsyncMock();monkeypatch.setattr(scan_manager,"executor",executor)
    with TestClient(create_app()) as client:
        from app.database.connection import db_session
        from tests.workspace_fixtures import bind_internal_workspace
        from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
        with db_session() as c:
            bind_internal_workspace(c,request)
            c.execute("INSERT INTO users(id,email,display_name) VALUES('b@example.com','b@example.com','Member B')")
            c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES('member-b',?,'b@example.com','MEMBER','ACTIVE','fixture','fixture')",(PLANEBYTE_ORGANIZATION_ID,))
        yield client,executor


def payload():
    return {"cities":["Austin, United States","Dallas, United States"],"verticals":["dentists","home_services"],"target":8,"fixture":True,"request_id":str(uuid.uuid4())}


def test_campaign_expansion_idempotency_and_shared_workflow(client):
    api,executor=client
    assert api.put('/api/automation/controls',json={'scan_paused':False,'email_paused':True}).status_code==200
    from app.database.connection import db_session
    with db_session() as c:c.execute("INSERT INTO account_roles VALUES('b@example.com','OPERATOR','fixture','a@example.com')")
    config=payload();response=api.post("/api/campaigns",json=config)
    assert response.status_code==201,response.text
    campaign=response.json();assert len(campaign["runs"])==4
    assert sum(run["target"] for run in campaign["runs"])==8
    assert api.post("/api/campaigns",json=config).status_code==201
    assert executor.start.await_count==4
    for run in campaign["runs"]:run_fixture(run["id"])
    complete=api.get("/api/campaigns/"+campaign["id"]).json()
    assert complete["status"]=="COMPLETED"
    assert complete["counters"]["qualified"]==8
    leads=api.get("/api/intelligence/leads",params={"campaign":campaign["id"]}).json()
    assert len(leads["items"])==8
    lead_id=leads["items"][0]["id"]
    changed=api.patch(f"/api/leads/{lead_id}/workflow",json={"lead_status":"SHORTLISTED","assigned_to":"b@example.com"})
    assert changed.status_code==200,changed.text
    assert changed.json()["assigned_to"]=="b@example.com"
    note=api.post(f"/api/leads/{lead_id}/notes",json={"body":"Review public service pages."},headers={"x-le-user":"b@example.com"})
    assert note.status_code==201
    assert note.json()["notes"][0]["created_by"]=="b@example.com"
    assert api.patch(f"/api/leads/{lead_id}/workflow",json={"assigned_to":"outside@example.com"}).status_code==422
    assert api.get(f"/api/scans/{campaign['runs'][0]['id']}/export/csv").status_code==200
    report=api.post(f"/api/leads/{lead_id}/report")
    assert report.status_code==409,report.text
    assert api.get("/api/reports").status_code==200


@pytest.mark.parametrize("params",[{"page_size":101},{"page":0},{"sort_by":"injected"},{"sort_dir":"invalid"},{"min_security":101}])
def test_server_filter_bounds(client,params):
    assert client[0].get("/api/intelligence/leads",params=params).status_code==422
