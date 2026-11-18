"""Comprehensive unit & integration tests for Workspace UX, ICP Intelligence, Notifications Center, and Full-Page AI Assistant."""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException

from app.database.connection import db_session
from app.database.migrations import run_migrations
from app.database.prospects import now
from app.icp import models as icp_models
from app.icp import service as icp_service
from app.intent_radar import agent_tools, assistant_chat
from app.notifications import center as notif_center
from app.notifications import transactional as mail
from app.platform.context import workspace_scope


def _seed_workspace(c, org_id: str, actor: str, *, role: str = "OWNER"):
    from app.api.organization import ensure_user
    ts = now()
    ensure_user(c, actor)
    c.execute(
        "INSERT INTO organizations(id,name,slug,status,created_at,updated_at) VALUES(?,?,?,'ACTIVE',?,?)",
        (org_id, f"Workspace {org_id[:6]}", f"ws-{org_id[:8]}", ts, ts),
    )
    c.execute(
        "INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE',?,?)",
        (str(uuid.uuid4()), org_id, actor, role, ts, ts),
    )
    c.execute(
        "INSERT INTO organization_onboarding(organization_id,status,current_step,created_at,updated_at) VALUES(?,'COMPLETED','COMPLETE',?,?)",
        (org_id, ts, ts),
    )
    c.execute(
        "INSERT INTO organization_products(organization_id,product,enabled,created_at,updated_at) VALUES(?,'INTENT_RADAR',1,?,?)",
        (org_id, ts, ts),
    )


def _seed_signal(c, org_id: str, title: str, excerpt: str, score: int = 86, source: str = "hacker_news") -> str:
    sid = str(uuid.uuid4())
    ts = now()
    c.execute(
        "INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json,status,available,revision) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,1)",
        (
            sid,
            org_id,
            source,
            sid[:12],
            f"https://news.ycombinator.com/item?id={sid[:8]}",
            title,
            excerpt,
            ts,
            ts,
            "Buying Intent",
            score,
            json.dumps({"provenance": {"fetch_method": "public_api", "content_kind": "discussion"}}),
            "New",
        ),
    )
    return sid


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "workspace_ux_test.db"
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("HEYSOW_MULTI_WORKSPACE_ENABLED", "true")
    monkeypatch.setenv("INTENT_RADAR_STAGE", "Beta")
    monkeypatch.setenv("INTENT_RADAR_GROWTH_ENABLED", "true")
    monkeypatch.setenv("INTENT_RADAR_AI_ENABLED", "false")
    monkeypatch.setenv("INTENT_RADAR_YOUTUBE_AI_ANALYTICS_ENABLED", "false")
    import app.config.settings as cfg_mod
    cfg_mod._settings_instance = None
    run_migrations()
    yield db_file
    cfg_mod._settings_instance = None


def test_icp_extended_criteria_primary_related_compare_and_delete(test_db):
    org = str(uuid.uuid4())
    actor = "owner@planebyte.test"
    with db_session() as c:
        _seed_workspace(c, org, actor)
        _seed_signal(
            c,
            org,
            "Looking for a HubSpot alternative for B2B SaaS outbound signals",
            "Our RevOps team needs better buying intent detection and SaaS workflow automation.",
            score=91,
        )
        _seed_signal(
            c,
            org,
            "Comparing observability tools for Kubernetes clusters",
            "Evaluating Datadog vs Grafana for distributed tracing.",
            score=62,
        )

        with workspace_scope(c, actor, org):
            icp1 = icp_service.create(
                c,
                icp_models.Create(
                    name="B2B SaaS RevOps Teams",
                    description="Mid-market B2B SaaS revenue teams seeking buying signals",
                    status="ACTIVE",
                    request_id=uuid.uuid4(),
                    criteria=icp_models.Criteria(
                        company=icp_models.CompanyCriteria(industries=["B2B SaaS"]),
                        intent=icp_models.IntentCriteria(
                            pain_points=["buying intent detection"],
                            business_needs=["RevOps workflow automation"],
                            competitors=["HubSpot", "Apollo"],
                            budget_indicators=["annual contract"],
                            preferred_sources=["hacker_news", "github"],
                            search_terms=["HubSpot alternative", "RevOps"],
                            custom_criteria=["Series A+"],
                        ),
                    ),
                ),
            )
            icp2 = icp_service.create(
                c,
                icp_models.Create(
                    name="DevOps Observability",
                    description="Infrastructure engineers",
                    status="ACTIVE",
                    request_id=uuid.uuid4(),
                    criteria=icp_models.Criteria(
                        company=icp_models.CompanyCriteria(industries=["DevOps"]),
                        intent=icp_models.IntentCriteria(search_terms=["Kubernetes", "Datadog"]),
                    ),
                ),
            )

            assert icp1["criteria"]["intent"]["competitors"] == ["HubSpot", "Apollo"]
            assert icp1["criteria"]["intent"]["custom_criteria"] == ["Series A+"]

            # Set primary ICP
            promoted = icp_service.set_primary(c, icp1["id"])
            assert promoted["is_primary"] is True

            # Related entities
            rel = icp_service.related(c, icp1["id"])
            assert len(rel["signals"]) >= 1

            # Compare & prioritize
            cmp_res = icp_service.compare_profiles(c)
            assert len(cmp_res["items"]) == 2
            assert cmp_res["recommended_id"] == icp1["id"]
            icp1_row = next(r for r in cmp_res["items"] if r["id"] == icp1["id"])
            assert icp1_row["high_intent_matches"] >= 1
            assert cmp_res["recommendation_reason"]

            # Soft-delete primary ICP clears default_icp_id cleanly
            deleted = icp_service.delete(c, icp1["id"])
            assert deleted["deleted"] is True
            remaining = icp_service.listing(c)["items"]
            assert len(remaining) == 1
            assert remaining[0]["id"] == icp2["id"]


def test_notifications_center_dedupe_preferences_tenant_isolation_and_resend_html(test_db):
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    actor_a = "alice@ws-a.test"
    actor_b = "bob@ws-b.test"

    with db_session() as c:
        _seed_workspace(c, org_a, actor_a)
        _seed_workspace(c, org_b, actor_b)

        nid1 = notif_center.emit(
            c,
            org_a,
            category="discovery",
            event_type="DISCOVERY_COMPLETED",
            title="Discovery completed (12 signals)",
            description="Scanned Hacker News & GitHub.",
            priority="high",
            resource_url="/intent-radar/discover/runs/123",
            dedupe_key="disc-run-123",
            recipient_email=actor_a,
        )
        # Duplicate dedupe_key must not create a second notification
        nid_dup = notif_center.emit(
            c,
            org_a,
            category="discovery",
            event_type="DISCOVERY_COMPLETED",
            title="Discovery completed (12 signals)",
            description="Duplicate",
            priority="high",
            dedupe_key="disc-run-123",
            recipient_email=actor_a,
        )
        assert nid1 is not None
        assert nid_dup is None

        notif_center.emit(
            c,
            org_a,
            category="security",
            event_type="API_KEY_CREATED",
            title="API key created: CI runner",
            description="Scoped API key created.",
            priority="high",
            resource_url="/settings?category=integrations&tab=api-keys",
            dedupe_key="key-created-1",
            recipient_email=actor_a,
        )

        # Workspace B sees ZERO notifications from Workspace A
        with workspace_scope(c, actor_b, org_b):
            b_list = notif_center.list_notifications(c)
            assert b_list["total"] == 0
            assert b_list["unread_count"] == 0
            with pytest.raises(HTTPException) as exc:
                notif_center.mark_read(c, nid1)
            assert exc.value.status_code == 404

        # Workspace A filters, marks read, updates preferences
        with workspace_scope(c, actor_a, org_a):
            a_list = notif_center.list_notifications(c)
            assert a_list["total"] == 2
            assert a_list["unread_count"] == 2

            sec_only = notif_center.list_notifications(c, category="security")
            assert sec_only["total"] == 1
            assert sec_only["items"][0]["category"] == "security"

            notif_center.mark_read(c, nid1)
            assert notif_center.list_notifications(c)["unread_count"] == 1

            notif_center.mark_all_read(c)
            assert notif_center.list_notifications(c)["unread_count"] == 0

            # Preferences: security & billing remain mandatory even if caller sends False
            updated_prefs = notif_center.update_preferences(
                c,
                notif_center.NotificationPreferencesUpdate(
                    email_cadence="daily_digest",
                    quiet_hours_enabled=True,
                    categories={"discovery": False, "security": False, "billing": False},
                ),
            )
            assert updated_prefs["email_cadence"] == "daily_digest"
            assert updated_prefs["categories"]["discovery"] is False
            assert updated_prefs["categories"]["security"] is True
            assert updated_prefs["categories"]["billing"] is True

            # Saving Intent Radar research preferences must preserve user_notification_preferences
            from app.intent_radar import models as radar_models
            from app.intent_radar import service as radar_service

            cur_pref = radar_service.preferences(c)
            radar_service.preferences(
                c,
                radar_models.Preferences(min_relevance=55, revision=cur_pref["revision"]),
            )
            reloaded_prefs = notif_center.get_preferences(c)
            assert reloaded_prefs["email_cadence"] == "daily_digest"
            assert reloaded_prefs["quiet_hours_enabled"] is True

    # Branded Resend HTML template rendering check
    subject, text, html = mail.render(
        "NOTIFICATION_ALERT",
        {
            "title": "High-relevance signal found",
            "message": "A founder asked for a HubSpot alternative on Hacker News.",
            "category": "signals",
            "cta_label": "Review signal",
            "cta_url": "https://app.planebyte.com/intent-radar/signals/abc",
        },
    )
    assert "High-relevance signal found" in subject
    assert "PlaneByte" in html
    assert "Review signal" in html
    assert "https://app.planebyte.com/intent-radar/signals/abc" in text


def test_ai_assistant_streaming_read_tools_action_approval_and_isolation(test_db):
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    actor_a = "founder@ws-a.test"
    actor_b = "other@ws-b.test"

    with db_session() as c:
        _seed_workspace(c, org_a, actor_a)
        _seed_workspace(c, org_b, actor_b)
        _seed_signal(
            c,
            org_a,
            "Need a lightweight CRM alternative for developer tools startups",
            "Looking for buying intent tools that integrate with GitHub.",
            score=89,
        )
        c.commit()

    async def collect_sse(actor: str, org: str, body: assistant_chat.ChatRequest):
        events = []
        async for raw in assistant_chat.stream_chat(actor, org, body):
            ev_name = ""
            ev_data = {}
            for line in raw.strip().split("\n"):
                if line.startswith("event:"):
                    ev_name = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    ev_data = json.loads(line.split(":", 1)[1].strip())
            events.append((ev_name, ev_data))
        return events

    # 1. Workspace summary query -> zero AI quota, structured metrics card, dynamic follow-ups
    events_1 = asyncio.run(
        collect_sse(
            actor_a,
            org_a,
            assistant_chat.ChatRequest(prompt="Summarize my workspace today and check sources policy"),
        )
    )
    event_names = [e[0] for e in events_1]
    assert "tool_start" in event_names
    assert "cards" in event_names
    assert "delta" in event_names
    assert "followups" in event_names
    assert "done" in event_names

    done_msg = next(e[1]["message"] for e in events_1 if e[0] == "done")
    assert done_msg["ai_consumed"] is False
    assert len(done_msg["followups"]) >= 2
    thread_id = done_msg["thread_id"]

    # Verify YouTube AI policy is truthfully surfaced as disabled
    sources_card = next((c_item for c_item in done_msg["cards"] if c_item["kind"] == "sources"), None)
    assert sources_card is not None
    assert sources_card["youtube_ai_analytics_enabled"] is False

    # 2. Action proposal flow (Create Monitor -> pending proposal -> NEVER auto-executed!)
    events_2 = asyncio.run(
        collect_sse(
            actor_a,
            org_a,
            assistant_chat.ChatRequest(
                prompt="Create an active monitor tracking HubSpot alternatives and CRM migrations",
                thread_id=uuid.UUID(thread_id),
            ),
        )
    )
    done_2 = next(e[1]["message"] for e in events_2 if e[0] == "done")
    assert len(done_2["proposals"]) == 1
    prop = done_2["proposals"][0]
    assert prop["tool"] == "create_monitor"
    assert prop["status"] == "pending"

    with db_session() as c:
        # Monitor must NOT exist yet before user confirms
        assert c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=?", (org_a,)).fetchone()[0] == 0

        # Cross-tenant execution must be blocked (404)
        with workspace_scope(c, actor_b, org_b):
            with pytest.raises(HTTPException) as exc:
                assistant_chat.execute_proposal(c, prop["action_id"])
            assert exc.value.status_code == 404

        # Owner approves & executes -> creates real monitor + audit log + idempotent replay
        with workspace_scope(c, actor_a, org_a):
            exec_res = assistant_chat.execute_proposal(c, prop["action_id"])
            assert exec_res["status"] == "executed"
            assert exec_res["result"]["entity_type"] == "monitor"
            assert c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=?", (org_a,)).fetchone()[0] == 1

            # Idempotent second call does NOT duplicate monitor
            replay = assistant_chat.execute_proposal(c, prop["action_id"])
            assert replay["idempotent_replay"] is True
            assert c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=?", (org_a,)).fetchone()[0] == 1

            # Action history recorded
            hist = agent_tools.list_action_history(c)
            assert len(hist["items"]) == 1
            assert hist["items"][0]["tool"] == "create_monitor"

            # Conversation management: rename, pin, archive, delete
            patched = assistant_chat.update_conversation(
                c, thread_id, assistant_chat.ConversationPatch(title="RevOps Strategy", pinned=True)
            )
            assert patched["title"] == "RevOps Strategy"
            assert patched["pinned"] is True

            listed = assistant_chat.list_conversations(c, search="RevOps")["items"]
            assert len(listed) == 1
            assert listed[0]["message_count"] == 2

            assistant_chat.delete_conversation(c, thread_id)
            assert assistant_chat.list_conversations(c)["items"] == []
