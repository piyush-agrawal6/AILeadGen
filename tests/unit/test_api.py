import pytest
from starlette.testclient import TestClient

from app.api.server import app
from app.database.connection import db_session
from app.database.models import Business, LeadScore, PipelineRun, PipelineRunEvent
from app.database.repositories import (
    BusinessRepository,
    LeadScoreRepository,
    PipelineRunEventRepository,
    PipelineRunRepository,
)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_markets(client):
    resp = client.get("/api/markets")
    assert resp.status_code == 200
    markets = resp.json()
    assert len(markets) > 0
    assert any("Austin" in m["city"] for m in markets)


def test_get_verticals(client):
    resp = client.get("/api/verticals")
    assert resp.status_code == 200
    verticals = resp.json()
    assert len(verticals) > 0
    assert any(v["key"] == "restaurant" for v in verticals)


def test_get_dashboard(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert "tier_distribution" in data
    assert "recommended_services" in data
    assert "score_distribution" in data
    assert "recent_scans" in data


def test_scans_lifecycle_and_events(client, monkeypatch):
    from app.api.services.scan_manager import scan_manager

    async def mock_start(*args, **kwargs):
        pass

    async def mock_resume(*args, **kwargs):
        return True

    monkeypatch.setattr(scan_manager.executor, "start", mock_start)
    monkeypatch.setattr(scan_manager.executor, "resume", mock_resume)

    with db_session() as conn:
        run_repo = PipelineRunRepository(conn)
        evt_repo = PipelineRunEventRepository(conn)

        run = PipelineRun(
            market="Test City, TX, USA",
            vertical="restaurant",
            target=25,
            status="RUNNING",
        )
        run_id = run_repo.create(run)

        evt = PipelineRunEvent(
            run_id=run_id,
            stage="DISCOVERY",
            event_type="DISCOVERY_COMPLETE",
            message="Discovered 50 test listings",
            completed=50,
            total=50,
        )
        evt_repo.create(evt)
        conn.commit()

    # Get scan detail
    detail_resp = client.get(f"/api/scans/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == run_id
    assert detail_resp.json()["status"] == "RUNNING"

    # Get scan events
    events_resp = client.get(f"/api/scans/{run_id}/events")
    assert events_resp.status_code == 200
    evts = events_resp.json()
    assert len(evts) >= 1
    assert evts[0]["event_type"] == "DISCOVERY_COMPLETE"

    # Cancel scan
    cancel_resp = client.post(f"/api/scans/{run_id}/cancel")
    assert cancel_resp.status_code == 200

    # Resume scan
    resume_resp = client.post(f"/api/scans/{run_id}/resume")
    assert resume_resp.status_code == 200


def test_leads_search_and_detail(client):
    with db_session() as conn:
        biz_repo = BusinessRepository(conn)
        score_repo = LeadScoreRepository(conn)

        b = Business(
            name="API Test Bistro",
            normalized_name="api test bistro",
            vertical="restaurant",
            city="Austin",
            state="Texas",
            country="United States",
            website="https://apitestbistro.com",
            domain="apitestbistro.com",
            public_email="contact@apitestbistro.com",
            processing_status="QUALIFIED",
        )
        b_id = biz_repo.insert(b)

        score = LeadScore(
            business_id=b_id,
            total_score=85.5,
            tier="A+",
            website_score=45.0,
            seo_opportunity_score=18.0,
            vertical_opportunity_score=14.0,
            contactability_score=8.5,
            recommended_service="Website Redesign + Local SEO",
            recommended_angle="Modernize online presence",
            score_breakdown={"website": 45.0},
        )
        score_repo.upsert(score)
        conn.commit()

    # Search leads
    search_resp = client.get(f"/api/leads?search=Bistro&tier=A%2B")
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["total"] >= 1
    assert any(item["name"] == "API Test Bistro" for item in data["items"])

    # Detail lead
    detail_resp = client.get(f"/api/leads/{b_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["business"]["name"] == "API Test Bistro"
    assert detail["score"]["tier"] == "A+"
    assert detail["score"]["total"] == 85.5

    # Generate report
    report_resp = client.post(f"/api/leads/{b_id}/report")
    assert report_resp.status_code == 200
    assert report_resp.json()["success"] is True

    # Download report
    dl_resp = client.get(f"/api/leads/{b_id}/report")
    assert dl_resp.status_code == 200
    assert "text/html" in dl_resp.headers["content-type"]


def test_settings_get_and_update(client):
    get_resp = client.get("/api/settings")
    assert get_resp.status_code == 200
    settings_data = get_resp.json()
    assert "crawler" in settings_data
    assert "auditing" in settings_data

    # Update crawler max pages
    settings_data["crawler"]["max_pages"] = 12
    put_resp = client.put("/api/settings", json=settings_data)
    assert put_resp.status_code == 200
    assert put_resp.json()["crawler"]["max_pages"] == 12


def test_system_doctor(client):
    resp = client.get("/api/system/doctor")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert len(data["diagnostics"]) > 0
