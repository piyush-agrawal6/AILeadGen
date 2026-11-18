"""Integrations 3.0 & Developer Platform 3.0 unit + protocol + security tests."""
from __future__ import annotations

import json
import uuid
import pytest
import httpx2
from fastapi.testclient import TestClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.api.organization import create_organization
from app.api.server import app, create_app
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.developer import keys
from app.intent_radar import source_policy
from app.platform.context import workspace_scope


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "http://testserver")
    s = get_settings()
    monkeypatch.setattr(s, "database_path", str(tmp_path / "int_dev_3.db"))
    monkeypatch.setattr(s, "allowed_user_emails", "owner@example.test,foreign@example.test")
    monkeypatch.setattr(s, "heysow_developer_api_enabled", True)
    monkeypatch.setattr(s, "heysow_mcp_enabled", True)
    monkeypatch.setattr(s, "heysow_workspace_management_enabled", True)
    monkeypatch.setattr(s, "intent_radar_stage", "Beta")
    monkeypatch.setattr(s, "intent_radar_growth_enabled", True)
    monkeypatch.setattr(s, "intent_radar_sources_v2_enabled", True)
    monkeypatch.setattr(s, "intent_radar_github_enabled", True)
    monkeypatch.setattr(s, "intent_radar_bluesky_enabled", True)
    monkeypatch.setattr(s, "intent_radar_youtube_ai_analytics_enabled", False)
    monkeypatch.setattr(s, "intent_radar_approved_feed_hosts", "github.com;rss.arxiv.org;community.n8n.io;www.youtube.com")
    monkeypatch.setattr(s, "mcp_allowed_hosts", "testserver")
    monkeypatch.setattr(s, "mcp_allowed_origins", "http://testserver")
    with TestClient(app) as http:
        with db_session() as c:
            c.execute(
                "UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",
                (INTERNAL,),
            )
            foreign = create_organization(c, "foreign@example.test", "Foreign Org")["organization_id"]
            c.execute(
                "UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",
                (foreign,),
            )
            c.execute(
                "UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",
                (foreign,),
            )
        yield http, s, foreign


def test_centralized_source_policy_enforces_youtube_and_discourse_gates(env):
    http, s, _ = env
    res = http.get("/api/intent-radar/sources/policies")
    assert res.status_code == 200
    items = {p["provider_id"]: p for p in res.json()["items"]}
    assert set(items.keys()) >= {"hacker_news", "stack_exchange", "github", "youtube", "bluesky", "atom", "discourse", "rss"}
    assert items["hacker_news"]["ai_processing_authorized"] is True
    assert items["github"]["ai_processing_authorized"] is True
    assert items["bluesky"]["ai_processing_authorized"] is True
    assert items["youtube"]["ai_processing_authorized"] is False
    assert items["youtube"]["missing_approval_note"]
    assert items["discourse"]["ai_processing_authorized"] is False
    assert items["discourse"]["missing_approval_note"]

    # Feed-level policy enforcement cannot be bypassed
    yt_policy = source_policy.evaluate_feed_policy(
        {"endpoint": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw", "family": "atom"}
    )
    assert yt_policy["ai_processing_authorized"] is False

    gh_policy = source_policy.evaluate_feed_policy(
        {"endpoint": "https://github.com/vercel/next.js/releases.atom", "family": "atom"}
    )
    assert gh_policy["ai_processing_authorized"] is True

    disc_policy = source_policy.evaluate_feed_policy(
        {"endpoint": "https://community.n8n.io/latest.rss", "family": "discourse"}
    )
    assert disc_policy["ai_processing_authorized"] is False

    # Runtime AI gate blocks YouTube and unapproved Discourse signals
    ok_yt, reason_yt = source_policy.can_run_ai_analysis({"source": "YouTube", "source_url": "https://www.youtube.com/watch?v=123", "evidence": {}})
    assert ok_yt is False and "YouTube" in (reason_yt or "")

    ok_disc, reason_disc = source_policy.can_run_ai_analysis({"source": "Approved Discourse", "source_url": "https://community.n8n.io/t/1", "evidence": {"provenance": {}}})
    assert ok_disc is False and "Discourse" in (reason_disc or "")


def test_custom_feeds_duplicate_prevention_bulk_toggle_delete_and_rss_truthfulness(env):
    http, _, _ = env
    # Capabilities should report 'No custom feeds' for RSS when 0 custom RSS feeds exist
    caps = http.get("/api/intent-radar/capabilities").json()
    rss_src = next(s for s in caps["sources"] if s.get("id") == "rss")
    assert rss_src["availability_label"] == "No custom feeds"
    assert rss_src["policy"]["provider_id"] == "rss"

    # Create a custom feed (client attempts to self-declare ai_processing_authorized=True on Discourse -> must be overridden to False!)
    payload = {
        "name": "n8n Community",
        "family": "discourse",
        "endpoint": "https://community.n8n.io/latest.rss",
        "policy_reference": "Public Discourse RSS",
        "attribution": "n8n Community",
        "retention_days": 7,
        "polling_minutes": 60,
        "enabled": True,
        "ai_processing_authorized": True,
    }
    first = http.post("/api/intent-radar/sources/configurations", json=payload)
    assert first.status_code == 201
    created = first.json()
    assert created["ai_processing_authorized"] is False
    feed_id = created["id"]

    # Duplicate endpoint must return 409 Conflict
    dup = http.post("/api/intent-radar/sources/configurations", json=payload)
    assert dup.status_code == 409

    # Bulk disable
    bulk = http.post(
        "/api/intent-radar/sources/configurations/bulk",
        json={"ids": [feed_id], "enabled": False},
    )
    assert bulk.status_code == 200 and bulk.json()["updated"] == 1
    listed = http.get("/api/intent-radar/sources/configurations").json()["items"]
    assert next(x for x in listed if x["id"] == feed_id)["enabled"] is False

    # Delete custom feed
    deleted = http.delete(f"/api/intent-radar/sources/configurations/{feed_id}")
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True


def test_developer_rest_api_v1_intent_endpoints_isolation_and_diagnostics(env):
    http, _, foreign = env
    # Issue scoped key for INTERNAL workspace
    issued = http.post(
        "/api/organization/developer/keys",
        json={"name": "Intent Platform 3.0 Key", "scopes": ["intent:read", "mcp:use"]},
    )
    assert issued.status_code == 201
    key_obj = issued.json()["key"]
    assert key_obj["key_prefix"].startswith("pbk_")
    assert key_obj["status"] == "Active"
    token = issued.json()["token"]
    headers = {"authorization": f"Bearer {token}"}

    # Verify all new bounded Intent Radar v1 endpoints respond 200 and include rate-limit headers
    for path in (
        "/api/v1/intent-radar/workspace",
        "/api/v1/intent-radar/sources",
        "/api/v1/intent-radar/signals",
        "/api/v1/intent-radar/discoveries",
        "/api/v1/intent-radar/saved-searches",
        "/api/v1/intent-radar/monitors",
        "/api/v1/intent-radar/opportunities",
        "/api/v1/intent-radar/icps",
    ):
        resp = http.get(path, headers=headers)
        assert resp.status_code == 200, f"{path} failed: {resp.status_code} {resp.text}"
        assert "x-ratelimit-limit" in {k.lower() for k in resp.headers.keys()}

    # OpenAPI includes new /v1/intent-radar/* endpoints
    spec = http.get("/api/v1/openapi.json", headers=headers).json()
    assert "/v1/intent-radar/signals" in spec["paths"]
    assert "/v1/intent-radar/discoveries" in spec["paths"]
    assert "/v1/intent-radar/sources" in spec["paths"]

    # Missing scope (mcp:use only, no intent:read) -> 403 Forbidden
    mcp_only = http.post(
        "/api/organization/developer/keys",
        json={"name": "MCP only", "scopes": ["mcp:use"]},
    ).json()["token"]
    assert http.get("/api/v1/intent-radar/signals", headers={"authorization": f"Bearer {mcp_only}"}).status_code == 403

    # Diagnostics & Usage endpoints for signed-in workspace admin
    diag = http.post("/api/organization/developer/diagnostics", json={})
    assert diag.status_code == 200
    djson = diag.json()
    assert djson["ok"] is True
    assert djson["rest_api"]["endpoint_count"] >= 8
    assert djson["mcp"]["oauth_2_1_supported"] is False
    assert "planebyte://sources/policies" in djson["mcp"]["resources"]

    usage = http.get("/api/organization/developer/usage")
    assert usage.status_code == 200
    assert usage.json()["keys"]["active"] >= 2


@pytest.mark.asyncio
async def test_mcp_extended_tools_and_authenticated_resources(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "http://testserver")
    s = get_settings()
    monkeypatch.setattr(s, "database_path", str(tmp_path / "mcp3.db"))
    monkeypatch.setattr(s, "allowed_user_emails", "owner@example.test")
    monkeypatch.setattr(s, "heysow_developer_api_enabled", True)
    monkeypatch.setattr(s, "heysow_mcp_enabled", True)
    monkeypatch.setattr(s, "heysow_workspace_management_enabled", True)
    monkeypatch.setattr(s, "intent_radar_stage", "Beta")
    monkeypatch.setattr(s, "mcp_allowed_hosts", "testserver")
    monkeypatch.setattr(s, "mcp_allowed_origins", "http://testserver")

    application = create_app()
    async with application.router.lifespan_context(application):
        with db_session() as c:
            c.execute(
                "UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",
                (INTERNAL,),
            )
            with workspace_scope(c, "owner@example.test", INTERNAL):
                issued = keys.create(c, keys.Create(name="MCP 3.0 Client", scopes=["mcp:use", "intent:read"]))

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
            base_url="http://testserver",
            headers={"authorization": "Bearer " + issued["token"]},
            timeout=15,
        ) as http:
            async with Client(
                streamable_http_client("http://testserver/api/v1/mcp", http_client=http, terminate_on_close=False),
                read_timeout_seconds=10,
            ) as client:
                tools = {t.name for t in (await client.list_tools()).tools}
                assert {"list_intent_discoveries", "get_intent_discovery", "list_saved_searches", "list_intent_icps"} <= tools

                disc = await client.call_tool("list_intent_discoveries", {"limit": 5})
                assert not disc.is_error and "items" in disc.structured_content

                resources = await client.list_resources()
                uris = {str(r.uri) for r in resources.resources}
                assert {
                    "planebyte://workspace/context",
                    "planebyte://sources/catalog",
                    "planebyte://sources/policies",
                } <= uris

                pol = await client.read_resource("planebyte://sources/policies")
                parsed = json.loads(pol.contents[0].text)
                assert any(p["provider_id"] == "youtube" and p["ai_processing_authorized"] is False for p in parsed["items"])
