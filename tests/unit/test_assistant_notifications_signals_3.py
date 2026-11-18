"""End-to-end regression tests for AI Assistant 3.0, Notifications & Monitoring Reliability, and Intent Signals 3.0."""
from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from test_prospecting_only import owned  # noqa: F401
from app.config.settings import get_settings
from app.database.prospects import now
from app.icp import models as icp_models, service as icp_service
from app.intelligence import jobs
from app.intent_radar import (
    agent_tools,
    assistant_chat,
    discovery,
    intelligence,
    models,
    opportunity_policy,
    providers,
    service,
)
from app.notifications import center
from app.platform.context import workspace_scope


@pytest.fixture
def env(owned, monkeypatch):  # noqa: F811
    c, path, org, _other = owned
    s = get_settings()
    monkeypatch.setattr(s, "database_path", str(path))
    monkeypatch.setattr(s, "intent_radar_stage", "Beta")
    monkeypatch.setattr(s, "intent_radar_growth_enabled", True)
    monkeypatch.setattr(s, "intent_radar_ai_enabled", True)
    monkeypatch.setattr(s, "heysow_workspace_management_enabled", True)
    monkeypatch.setattr(s, "billing_enabled", False)
    monkeypatch.setattr(s, "allowed_user_emails", "controlled@example.test,foreign@example.test")
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org,))
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
    c.execute(
        "INSERT OR IGNORE INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), org, "foreign@example.test", "MEMBER", "ACTIVE", now(), now()),
    )
    c.commit()
    return c, path, org


def _insert_signal(
    c,
    org: str,
    *,
    title: str = "Looking for a better B2B CRM alternative",
    excerpt: str = "We are evaluating alternatives to our current CRM platform and need recommendations.",
    source: str = "Hacker News",
    category: str = "Recommendation request",
    score: int = 86,
    status: str = "New",
    intent_phrase: str | None = "evaluating alternatives",
) -> str:
    sid = str(uuid.uuid4())
    ev = {
        "matched_keywords": ["crm", "alternative"],
        "matched_topics": ["crm"],
        "intent_phrase": intent_phrase,
        "confidence": "High",
        "explanation": "Matched keywords and recommendation phrase",
        "observed_text": excerpt,
        "unknown": ["Buyer role and budget are unknown."],
        "penalties": [],
        "purchasing_event_verified": False,
        "provenance": {"fetch_method": "official_hn", "retention_days": 30},
    }
    stamp = now()
    c.execute(
        "INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json,status,available) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (sid, org, source, sid[:12], f"https://news.ycombinator.com/item?id={sid[:8]}", title, excerpt, stamp, stamp, category, score, json.dumps(ev), status),
    )
    c.commit()
    return sid


# ---------------------------------------------------------------------------
# PILLAR 1: AI Assistant 3.0 — Pre-action validation, tool fixes, persistence
# ---------------------------------------------------------------------------

def test_assistant_blocks_invalid_primary_icp_discovery_when_no_icp_exists(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        tools, direct_only = assistant_chat._plan_read_tools(
            "Run a discovery search for my primary ICP keywords", "overview", None
        )
        tool_names = [t[0] for t in tools]
        assert "list_icps" in tool_names
        assert "get_sources_health" in tool_names
        assert direct_only is True  # Pure action command uses 0 AI quota!

        by_tool = {name: agent_tools.execute_read_tool(c, name, params)["data"] for name, params in tools}
        proposal, validation_note = assistant_chat._detect_action_proposal(
            "Run a discovery search for my primary ICP keywords", "overview", None, by_tool, role="OWNER"
        )
        assert proposal is None
        assert validation_note is not None
        assert "0 Ideal Customer Profiles" in validation_note


def test_assistant_billing_check_uses_zero_ai_quota_and_sources_health_accurate(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        tools, direct_only = assistant_chat._plan_read_tools(
            "What is my current subscription plan, trial status, and remaining monthly search and AI allowance?",
            "overview",
            None,
        )
        assert direct_only is True
        assert any(t[0] == "get_billing_usage" for t in tools)

        allowed = agent_tools._allowed_sources(c)
        assert "hacker_news" in allowed
        sh = agent_tools.execute_read_tool(c, "get_sources_health")["data"]
        assert any(s["selectable"] for s in sh["sources"])


def test_assistant_proposal_lifecycle_execute_idempotency_and_failure_persistence(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        sid = _insert_signal(c, org, status="New")
        # 1. Successful execution of update_signal_status (was broken with non-existent Review model!)
        action_id = str(uuid.uuid4())
        turn_id = str(uuid.uuid4())
        body = assistant_chat.ChatRequest(prompt="Qualify signal")
        proposal = {
            "action_id": action_id,
            "tool": "update_signal_status",
            "title": "Qualify signal",
            "description": "Marks signal Qualified",
            "status": "pending",
            "params": {"signal_id": sid, "status": "Qualified", "notes": "Confirmed buyer"},
        }
        ctx = assistant_chat.analytics.access(c)
        assistant_chat._persist_turn(
            c,
            ctx=ctx,
            body=body,
            key=turn_id,
            thread_id=turn_id,
            markdown="Ready to qualify.",
            tool_calls=[],
            cards=[],
            proposals=[proposal],
            followups=[],
            citations=[],
            limitations=[],
            mode="Workspace data — 0 AI quota",
            model_name=None,
            ai_consumed=False,
        )
        c.commit()

        first = assistant_chat.execute_proposal(c, action_id)
        c.commit()
        assert first["status"] == "executed"
        assert first["result"]["data"]["status"] == "Qualified"
        assert service.get(c, "signals", sid)["status"] == "Qualified"

        # Idempotent replay returns same result without duplicating
        replay = assistant_chat.execute_proposal(c, action_id)
        assert replay.get("idempotent_replay") is True

        # 2. Failed execution persists 'failed' + error + FAILED audit log entry
        bad_action_id = str(uuid.uuid4())
        bad_turn_id = str(uuid.uuid4())
        bad_prop = {
            "action_id": bad_action_id,
            "tool": "create_icp",
            "title": "Create invalid ICP",
            "description": "Empty criteria",
            "status": "pending",
            "params": {"name": "Empty ICP", "industries": [], "pain_points": [], "keywords": []},
        }
        assistant_chat._persist_turn(
            c,
            ctx=ctx,
            body=assistant_chat.ChatRequest(prompt="Create empty ICP"),
            key=bad_turn_id,
            thread_id=bad_turn_id,
            markdown="Proposal prepared.",
            tool_calls=[],
            cards=[],
            proposals=[bad_prop],
            followups=[],
            citations=[],
            limitations=[],
            mode="Workspace data — 0 AI quota",
            model_name=None,
            ai_consumed=False,
        )
        c.commit()
        with pytest.raises(HTTPException) as exc:
            assistant_chat.execute_proposal(c, bad_action_id)
        assert exc.value.status_code == 422

        detail = assistant_chat.get_conversation_detail(c, bad_turn_id)
        persisted = detail["messages"][0]["proposals"][0]
        assert persisted["status"] == "failed"
        assert persisted.get("error")
        history = agent_tools.list_action_history(c)["items"]
        assert any(h["result"] == "FAILED" for h in history)


def test_assistant_run_discovery_emits_started_not_completed_notification(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        action_id = str(uuid.uuid4())
        res = agent_tools.execute_write_tool(
            c,
            "run_discovery",
            {"title": "CRM Search", "keywords": ["crm alternative"], "sources": ["hacker_news"]},
            action_id=action_id,
        )
        c.commit()
        assert res.get("_launch_job_id")
        notifs = center.list_notifications(c, category="ai")["items"]
        assert any("AI Assistant started: Run Discovery Search" in n["title"] for n in notifs)
        assert not any("AI Assistant completed: Run Discovery Search" in n["title"] for n in notifs)


# ---------------------------------------------------------------------------
# PILLAR 2: Notifications & Monitoring Reliability
# ---------------------------------------------------------------------------

def test_notifications_dedupe_categories_recipient_isolation_and_redaction(env, monkeypatch):
    c, path, org = env
    monkeypatch.setattr(providers.HackerNews, "fetch", AsyncMock(side_effect=TimeoutError("timeout")))
    with workspace_scope(c, "controlled@example.test", org):
        # 1. Ad-hoc discovery failure with 0 monitors -> category='discovery', NEVER 'monitoring' or 'signals'
        disc_job = discovery.create(c, models.Discovery(configuration=models.Search(keywords=["crm"])))
        c.commit()
        jobs.execute(disc_job["id"], path)
        listed = center.list_notifications(c)
        assert listed["total"] == 1
        assert listed["unread_count"] == 1
        item = listed["items"][0]
        assert item["category"] == "discovery"
        assert item["severity"] == "error"
        assert item["title"] == "Discovery search failed"
        assert item["url"].startswith("/intent-radar/discover/runs/")

        # 2. Monitor match alert writes both intent_alerts + workspace_notifications, but center deduplicates to 1!
        mon = service.save_monitor(c, models.Monitor(name="CRM Monitor", configuration=models.Search(keywords=["crm"]), status="Active"))
        sid = _insert_signal(c, org)
        service.alert(c, f"match:{mon['id']}:{sid}", "Monitor found a matching discussion", "Great match", mon["id"], sid, "controlled@example.test")
        c.commit()
        listed2 = center.list_notifications(c)
        assert listed2["total"] == 2
        assert listed2["unread_count"] == 2
        assert listed2["category_counts"]["monitoring"] == 1
        assert listed2["category_counts"]["discovery"] == 1

        # 3. Private notification for owner cannot be marked read by member
        priv_id = center.emit(
            c,
            org,
            category="ai",
            event_type="AI_PRIVATE",
            title="Owner private AI update",
            description="Only for owner",
            recipient_email="controlled@example.test",
        )
        c.commit()

        # 4. Signal redaction preserves __pb_notif__ JSON metadata
        sig_notif_id = center.emit(
            c,
            org,
            category="signals",
            event_type="SIGNAL_ANALYZED",
            title="High-relevance signal",
            description="Original excerpt text",
            signal_id=sid,
            recipient_email="controlled@example.test",
        )
        c.commit()
        center.redact_signal_alerts(c, org, sid)
        c.commit()
        redacted_item = next(i for i in center.list_notifications(c)["items"] if i["id"] == sig_notif_id)
        assert redacted_item["category"] == "signals"
        assert redacted_item["description"] == "Source content unavailable"

    # Member cannot read or mark owner's private notifications as read
    with workspace_scope(c, "foreign@example.test", org):
        member_list = center.list_notifications(c)
        assert all(i["id"] != priv_id for i in member_list["items"])
        with pytest.raises(HTTPException) as denied:
            center.mark_read(c, priv_id)
        assert denied.value.status_code == 404
        center.mark_all_read(c)
        c.commit()

    with workspace_scope(c, "controlled@example.test", org):
        owner_priv = next(i for i in center.list_notifications(c)["items"] if i["id"] == priv_id)
        assert owner_priv["read_at"] is None
        # Bulk read & unread works cleanly
        bulk_res = center.bulk_update(c, center.BulkNotificationAction(ids=[priv_id], action="read"))
        assert bulk_res["updated"] == 1
        owner_priv_after = next(i for i in center.list_notifications(c)["items"] if i["id"] == priv_id)
        assert owner_priv_after["read_at"] is not None


def test_monitors_listing_includes_signals_count(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        mon = service.save_monitor(c, models.Monitor(name="SaaS Tracker", configuration=models.Search(keywords=["saas"]), status="Active"))
        sid = _insert_signal(c, org)
        c.execute(
            "INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?)",
            (org, mon["id"], sid, now()),
        )
        c.commit()
        listing = service.listing(c, "monitors", status="Current")
        assert listing["items"][0]["signals_count"] == 1


# ---------------------------------------------------------------------------
# PILLAR 3: Intent Signals 3.0 — Lifecycle, Bulk Actions, High Intent, AI History
# ---------------------------------------------------------------------------

def test_signals_lifecycle_opportunity_eligibility_and_fast_bulk_actions(env):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        # Signal without explicit request phrase starts ineligible
        s_plain = _insert_signal(
            c,
            org,
            title="General discussion about databases",
            excerpt="Sharing architecture notes from our recent refactor.",
            category="General discussion",
            intent_phrase=None,
            status="New",
        )
        s_explicit = _insert_signal(
            c,
            org,
            title="Looking for CRM alternatives",
            excerpt="We are evaluating CRM software alternatives this quarter.",
            category="Alternative search",
            intent_phrase="evaluating CRM software alternatives",
            status="New",
        )
        s_atom = _insert_signal(
            c,
            org,
            title="Atom feed discussion",
            excerpt="Comparing workflow tools.",
            source="Atom",
            status="New",
        )

        # Source filter alias "Atom Feeds" matches DB source='Atom'!
        atom_list = service.listing(c, "signals", source="Atom Feeds")
        assert atom_list["total"] == 1
        assert atom_list["items"][0]["id"] == s_atom

        # Plain signal is ineligible before qualification
        assert service.get(c, "signals", s_plain)["opportunity_eligibility"]["eligible"] is False

        # Bulk opportunity creates for eligible, skips ineligible with explicit reason
        bulk_opp = service.bulk_action(c, models.Bulk(ids=[s_plain, s_explicit], action="opportunity"))
        assert bulk_opp["updated"] == 1
        assert bulk_opp["already_existed"] == 0
        assert len(bulk_opp["skipped"]) == 1
        assert bulk_opp["skipped"][0]["id"] == s_plain
        assert bulk_opp["skipped"][0]["reason"]

        # Re-running bulk opportunity counts already_existed without duplicating
        bulk_opp2 = service.bulk_action(c, models.Bulk(ids=[s_explicit], action="opportunity"))
        assert bulk_opp2["updated"] == 0
        assert bulk_opp2["already_existed"] == 1

        # Qualifying s_plain unlocks Opportunity eligibility!
        bulk_qual = service.bulk_action(c, models.Bulk(ids=[s_plain], action="qualify"))
        assert bulk_qual["updated"] == 1
        plain_after = service.get(c, "signals", s_plain)
        assert plain_after["status"] == "Qualified"
        assert plain_after["opportunity_eligibility"]["eligible"] is True

        # Dismissing s_explicit removes it from High Intent tab!
        assert any(i["id"] == s_explicit for i in service.listing(c, "signals", view="high_intent")["items"])
        service.bulk_action(c, models.Bulk(ids=[s_explicit], action="dismiss"))
        assert not any(i["id"] == s_explicit for i in service.listing(c, "signals", view="high_intent")["items"])

        # Bulk save + unsave works cleanly
        service.bulk_action(c, models.Bulk(ids=[s_plain], action="save"))
        assert service.get(c, "signals", s_plain)["saved"] is True
        service.bulk_action(c, models.Bulk(ids=[s_plain], action="unsave"))
        assert service.get(c, "signals", s_plain)["saved"] is False


def test_signal_ai_history_retains_icp_assessments_and_translations(env, monkeypatch):
    c, _, org = env
    with workspace_scope(c, "controlled@example.test", org):
        icp = icp_service.create(
            c,
            icp_models.Create(
                name="B2B SaaS CRM Buyers",
                description="Mid-market SaaS teams evaluating CRM tools",
                status="ACTIVE",
                request_id=uuid.uuid4(),
                criteria=icp_models.Criteria(
                    company=icp_models.CompanyCriteria(industries=["B2B SaaS"]),
                    intent=icp_models.IntentCriteria(
                        pain_points=["CRM migration"],
                        search_terms=["CRM alternative"],
                    ),
                ),
            ),
        )
        sid = _insert_signal(
            c,
            org,
            title="Need a CRM alternative for our B2B SaaS team",
            excerpt="Our B2B SaaS company is struggling with CRM migration and evaluating alternatives.",
        )
        c.commit()

        prefs = service.preferences(c)
        service.preferences(
            c,
            models.Preferences(
                default_view="table",
                min_relevance=0,
                topics=[],
                alerts_enabled=True,
                alert_threshold=85,
                source_retention_days=30,
                ai_assistance=True,
                analysis_daily_call_limit=10,
                analysis_daily_token_limit=50000,
                revision=prefs["revision"],
            ),
        )
        c.commit()

        fake_interp = intelligence.Interpretation(
            categories=["Alternative search"],
            claims=[
                intelligence.Claim(
                    kind="intent",
                    quote="evaluating alternatives",
                    interpretation="Explicitly evaluating alternative solutions.",
                    translation="Evaluando soluciones alternativas.",
                )
            ],
            summary=intelligence.Claim(
                kind="summary",
                quote="Need a CRM alternative",
                interpretation="A B2B SaaS team is seeking a CRM alternative.",
                translation="Un equipo B2B SaaS busca una alternativa de CRM.",
            ),
            buyer_problem=intelligence.Claim(
                kind="semantic",
                quote="struggling with CRM migration",
                interpretation="Experiencing friction during CRM migration.",
                target="CRM migration",
                translation="Experimentando problemas con la migración de CRM.",
            ),
            business_relevance=intelligence.Claim(
                kind="icp",
                quote="B2B SaaS company",
                interpretation="Matches B2B SaaS target industry.",
                target="CRM migration",
            ),
            detected_language="en",
            language_evidence="Need a CRM alternative",
            icp_assessments=[
                intelligence.CriterionAssessment(
                    criterion="company.industries",
                    status="MATCH",
                    quote="B2B SaaS company",
                    explanation="Explicitly states B2B SaaS company.",
                    basis="Unverified source context; not verified company or decision-maker",
                )
            ],
            uncertainty="Low",
            review_needed=False,
            recommended_research="Compare stated needs with offering",
        )

        class FakeGateway:
            last_model = "gemini-2.5-flash"
            last_provider = "vertex"
            last_usage = {"prompt_tokens": 100, "output_tokens": 50}

            async def structured(self, *args, **kwargs):
                return fake_interp

        monkeypatch.setattr(intelligence.ai, "provider", lambda _c: FakeGateway())
        res = asyncio.run(
            intelligence.analyze(
                c,
                sid,
                models.AnalysisRequest(icp_id=uuid.UUID(icp["id"]), summary_language="es"),
            )
        )
        c.commit()
        assert res["structured"]["translated_summary"] == "Un equipo B2B SaaS busca una alternativa de CRM."
        assert res["interpretation"]["icp_assessments"][0]["criterion"] == "company.industries"

        # CRITICAL REGRESSION CHECK: history() MUST NOT drop persisted ICP analyses on reload!
        hist = intelligence.history(c, sid)
        assert len(hist["items"]) == 1
        assert hist["items"][0]["structured"]["translated_summary"] == "Un equipo B2B SaaS busca una alternativa de CRM."
        assert hist["items"][0]["interpretation"]["icp_assessments"][0]["status"] == "MATCH"
