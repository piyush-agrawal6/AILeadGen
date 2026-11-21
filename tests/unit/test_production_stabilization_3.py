"""Production Stabilization & Dashboard 3.0 comprehensive regression suite."""
import asyncio
import json
import time
import uuid
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.organization import create_organization, memberships as list_org_memberships
from app.api.routes.domains import DomainPage
from app.api.routes.foundation import _safe_audit_details
from app.billing import subscription_access as access
from app.billing.subscription_schema import CONTRACT_SQL, EVENT_SQL
from app.database.discovery_workspace_schema import DISCOVERY_WORKSPACE_SQL
from app.database.prospects import now
from app.intent_radar import service as radar_service
from app.platform import company_profiles, domains, memberships, workspaces
from app.platform.context import workspace_scope
from app.platform.workspace_search import search_workspace
from test_subscription_payment import accounts, customer  # noqa: F401


@pytest.fixture
def env_db(customer, monkeypatch):
    c, s = customer
    c.executescript(EVENT_SQL + CONTRACT_SQL + DISCOVERY_WORKSPACE_SQL)
    c.commit()
    monkeypatch.setattr(s, "heysow_workspace_management_enabled", True)
    monkeypatch.setattr(s, "subscription_onboarding_required", True)
    monkeypatch.setattr(s, "subscription_terms_version", access.POLICY)
    monkeypatch.setattr(s, "creem_environment", "production")
    monkeypatch.setattr(s, "creem_api_key", SecretStr("synthetic"))
    monkeypatch.setattr(s, "intent_radar_stage", "Beta")
    monkeypatch.setattr(s, "intent_radar_growth_enabled", True)
    monkeypatch.setattr(s, "allowed_user_emails", "owner@planebyte.com,teammate@planebyte.com")
    return c, s


def _enable_workspace(c, org_id: str):
    c.execute(
        "UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",
        (org_id,),
    )
    c.execute(
        "UPDATE organization_onboarding SET status='COMPLETED', profile_completed=1, services_completed=1, audience_completed=1, preferences_completed=1 WHERE organization_id=?",
        (org_id,),
    )
    c.execute("DELETE FROM subscription_requirements WHERE organization_id=?", (org_id,))


def test_global_search_returns_signals_growth_company_with_zero_partial_errors_and_isolation(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w1 = create_organization(c, owner, "PlaneByte Labs")
    w2 = create_organization(c, owner, "Other Tenant")
    org1, org2 = w1["organization_id"], w2["organization_id"]
    _enable_workspace(c, org1)
    _enable_workspace(c, org2)

    stamp = now()
    # Seed company profile + service in org1
    c.execute(
        """INSERT INTO organization_profiles(organization_id, display_name, website_url, industry, short_description, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?)""",
        (org1, "PlaneByte Labs", "https://planebyte.com", "B2B SaaS", "Intent intelligence platform for revenue teams.", stamp, stamp),
    )
    c.execute(
        """INSERT INTO organization_services(id, organization_id, name, slug, category, description, active, source, created_at, updated_at)
           VALUES(?,?,?,?,?,?,1,'USER_CONFIRMED',?,?)""",
        (str(uuid.uuid4()), org1, "Webhook Radar", "webhook-radar", "Monitoring", "Real-time GitHub webhook signal monitor", stamp, stamp),
    )

    # Seed Intent Signals in org1 and org2
    sig1_id = str(uuid.uuid4())
    sig2_id = str(uuid.uuid4())
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'New',1,1)""",
        (sig1_id, org1, "GitHub", "gh-1", "https://github.com/org/repo/issues/1", "Looking for GitHub webhook intent tracking tool", "Need automated B2B buying signal alerts", stamp, stamp, "Buying Intent", 92, json.dumps({"provenance": {"retention_days": 30}})),
    )
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'New',1,1)""",
        (sig2_id, org2, "GitHub", "gh-2", "https://github.com/other/repo/issues/9", "Secret webhook roadmap for Other Tenant", "Confidential tenant two signal", stamp, stamp, "Buying Intent", 95, json.dumps({"provenance": {"retention_days": 30}})),
    )

    # Seed Growth Research report in org1
    rep_id = str(uuid.uuid4())
    c.execute(
        """INSERT INTO growth_research(id, organization_id, created_by, kind, question, title, scope_json, snapshot_json, output_json, input_hash, request_id, status, created_at, updated_at)
           VALUES(?,?,?,'REPORT','How do teams monitor GitHub webhooks?','Webhook Market Report','{}','{}','{}','hash-1',?,'COMPLETED',?,?)""",
        (rep_id, org1, owner, str(uuid.uuid4()), stamp, stamp),
    )

    with workspace_scope(c, owner, org1):
        res = search_workspace(c, organization_id=org1, actor=owner, query="webhook", category="all", limit=6)
        assert res["partial_errors"] == []
        signal_ids = [item["id"] for item in res["groups"]["signals"]]
        assert f"signal:{sig1_id}" in signal_ids
        assert f"signal:{sig2_id}" not in signal_ids
        intel_ids = [item["id"] for item in res["groups"]["intelligence"]]
        assert f"growth:{rep_id}" in intel_ids
        company_ids = [item["id"] for item in res["groups"]["company"]]
        assert any(cid.startswith("service:") for cid in company_ids)


def test_workspace_enrichment_reconciles_plan_and_real_onboarding_steps_without_leakage(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w1 = create_organization(c, owner, "PlaneByte")
    org1 = w1["organization_id"]
    w2 = create_organization(c, owner, "Syntaxwars")  # Independent billing by explicit setup in this fixture.
    org2 = str(w2["organization_id"])
    stamp = now()
    ts = int(time.time())

    # Org1 has completed onboarding + canceled-remaining 3-day Starter Trial
    c.execute(
        "UPDATE organization_onboarding SET status='COMPLETED', profile_completed=1, services_completed=1, audience_completed=1, preferences_completed=1 WHERE organization_id=?",
        (org1,),
    )
    checkout_id = str(uuid.uuid4())
    contract_id = str(uuid.uuid4())
    plan_json = json.dumps({"code": "starter", "name": "Starter", "limits": access.TRIAL_LIMITS})
    c.execute(
        """INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at)
           VALUES(?,?,?,'creem','production','starter','trial',?,'h1','cust_pb','prod_pb','COMPLETED','US','USD',0,3,?,?,'{}',?,?)""",
        (checkout_id, org1, owner, str(uuid.uuid4()), access.POLICY, stamp, stamp, stamp),
    )
    c.execute(
        """INSERT INTO subscription_contracts(id,organization_id,created_by,provider,environment,provider_id,customer_id,checkout_id,plan_code,plan_json,status,recurring_authorized,trial_start,trial_end,period_start,period_end,cancel_confirmed_at,verified_at,evidence_json,created_at,updated_at)
           VALUES(?,?,?,'creem','production','sub_pb','cust_pb',?,'starter',?,'canceled',0,?,?,?,?,?,?,?, ?,?)""",
        (contract_id, org1, owner, checkout_id, plan_json, ts - 3600, ts - 3600 + access.TRIAL_SECONDS, ts - 3600, ts - 3600 + access.TRIAL_SECONDS, stamp, stamp, "{}", stamp, stamp),
    )
    c.execute("INSERT INTO subscription_workspace_slots(organization_id,environment,contract_id) VALUES(?,'production',?)", (org1, contract_id))
    c.execute(
        "INSERT INTO subscription_trials(id,user_id,company_domain,organization_id,contract_id,policy_version,starts_at,ends_at) VALUES(?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), owner, "planebyte.com", org1, contract_id, access.POLICY, ts - 3600, ts - 3600 + access.TRIAL_SECONDS),
    )

    # Org2 has saved company profile & service (steps 1 & 2 done) but NO ICP and NO plan!
    c.execute(
        "INSERT INTO organization_profiles(organization_id, display_name, industry, short_description, created_at, updated_at) VALUES(?,?,?,?,?,?)",
        (org2, "Syntaxwars", "Developer Tools", "Competitive coding platform for engineering teams.", stamp, stamp),
    )

    enriched = workspaces.enrich_memberships(c, list_org_memberships(c, owner))
    by_id = {row["organization_id"]: row for row in enriched}

    pb = by_id[org1]
    assert pb["plan_label"] == "Starter Trial"
    assert pb["plan_status"] == "Canceled · Access remaining"
    assert pb["onboarding_completed_steps"] == 3
    assert pb["onboarding_total_steps"] == 3
    assert pb["next_setup_step"] is None

    syn = by_id[org2]
    assert syn["plan_label"] == "No active plan"
    assert syn["onboarding_completed_steps"] == 1
    assert syn["next_setup_step"] == "icp"
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(org2,))
    uncovered=next(r for r in workspaces.enrich_memberships(c,list_org_memberships(c,owner)) if r['organization_id']==org2)
    assert uncovered['plan_label']=='No active plan' and uncovered['onboarding_completed_steps']==3 and uncovered['next_setup_step'] is None


def test_overview_counts_active_opportunities_accurately(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Metrics Org")
    org = w["organization_id"]
    _enable_workspace(c, org)
    stamp = now()
    for idx, st in enumerate(("New", "Reviewing", "Saved", "Archived")):
        sig_id = str(uuid.uuid4())
        c.execute(
            """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'New',1,1)""",
            (sig_id, org, "Hacker News", f"hn-{idx}", f"https://news.ycombinator.com/item?id={idx+1}", f"Need CRM replacement #{idx}", "Looking for options", stamp, stamp, "Buying Intent", 90, json.dumps({"provenance": {"retention_days": 30}})),
        )
        c.execute(
            """INSERT INTO intent_opportunities(id, organization_id, signal_id, status, priority, notes, next_action, created_by, created_at, updated_at)
               VALUES(?,?,?,?,?,'note','follow up',?,?,?)""",
            (str(uuid.uuid4()), org, sig_id, st, "High", owner, stamp, stamp),
        )
    with workspace_scope(c, owner, org):
        ov = radar_service.overview(c, include_previews=False)
        assert ov["saved_opportunities"] == 3


def test_domains_validation_schema_and_honest_dns_feedback(env_db, monkeypatch):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Domain Org")
    org = w["organization_id"]

    # Reject IPs, localhost, internal TLDs, and malformed URLs
    for bad in ("127.0.0.1", "localhost", "app.local", "https://planebyte.com", "not a domain"):
        with pytest.raises(ValueError):
            domains.DomainCreate(domain=bad)

    with workspace_scope(c, owner, org):
        created = domains.challenge(c, domains.DomainCreate(domain="planebyte.com"))
        listing = domains.listing(c)
        validated = DomainPage.model_validate(listing)
        assert validated.items[0].record_name == "_heysow-verify.planebyte.com"
        assert validated.items[0].record_type == "TXT"
        assert validated.items[0].attempts == 0

        # Missing TXT record returns PENDING with clear diagnostic message (never faked!)
        monkeypatch.setattr(domains, "_resolve", Mock(return_value=[]))
        pending_res = asyncio.run(domains.verify(c, created["id"]))
        assert pending_res["status"] == "PENDING"
        assert pending_res["found_records_count"] == 0
        assert "No TXT record found yet" in pending_res["message"]


def test_company_profile_quality_flags_gibberish_and_preserves_valid_acronyms():
    bad_profile = {
        "name": "PlaneByte",
        "website": "https://planebyte.com",
        "industry": "xsx",
        "city": "saxas",
        "country": "xsas",
        "description": "xsx saxas xsas",
        "positioning": "",
        "countries_served": ["xsas"],
        "target_customers": ["SMBs", "CTOs", "B2B SaaS"],
        "target_industries": ["AI", "CRM"],
        "specialties": [],
        "products_services": [{"name": "Intent Radar", "category": "SaaS", "description": "Buying signal discovery"}],
    }
    issues = company_profiles.analyze_profile_quality(bad_profile)
    flagged_fields = {i["field"] for i in issues if i["severity"] == "warning"}
    assert "industry" in flagged_fields
    assert "city" in flagged_fields
    assert "country" in flagged_fields
    assert "description" in flagged_fields
    assert "countries_served" in flagged_fields
    # Legitimate acronyms SMBs, CTOs, B2B SaaS, AI, CRM must NOT be flagged!
    assert "target_customers" not in flagged_fields
    assert "target_industries" not in flagged_fields


def test_audit_details_recursively_scrubs_secrets_and_tokens():
    raw = json.dumps({
        "domain": "planebyte.com",
        "nested": {
            "api_key": "plain-secret-value",
            "note": "Authorization: Bearer super_secret_token_123",
            "key_preview": "pbk_12345678-1234-1234-1234-1234567890ab.secret",
            "safe": "visible-value",
        },
        "list_items": ["ghp_abcdefghijklmnopqrstuvwxyz123456", "normal-item"],
    })
    cleaned = _safe_audit_details(raw)
    assert cleaned["domain"] == "planebyte.com"
    assert cleaned["nested"]["api_key"] == "[redacted]"
    assert cleaned["nested"]["note"] == "[redacted]"
    assert cleaned["nested"]["key_preview"] == "[redacted]"
    assert cleaned["nested"]["safe"] == "visible-value"
    assert cleaned["list_items"] == ["[redacted]", "normal-item"]


def test_team_members_list_and_role_removal_isolation(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    teammate = "teammate@planebyte.com"
    w1 = create_organization(c, owner, "Team Org 1")
    w2 = create_organization(c, owner, "Team Org 2")
    org1, org2 = w1["organization_id"], w2["organization_id"]
    _enable_workspace(c, org1)
    _enable_workspace(c, org2)

    with workspace_scope(c, owner, org1):
        memberships.change_role(c, owner, teammate, "MEMBER")
        listed = memberships.list_members(c, owner)
        assert listed["total"] == 2
        assert {m["email"] for m in listed["items"]} == {owner, teammate}

    # Org2 must remain isolated (only owner)
    with workspace_scope(c, owner, org2):
        listed2 = memberships.list_members(c, owner)
        assert listed2["total"] == 1
        assert listed2["items"][0]["email"] == owner

    # Remove teammate from org1 works cleanly
    with workspace_scope(c, owner, org1):
        removed = memberships.remove_member(c, owner, teammate)
        assert removed["removed"] is True
        assert memberships.list_members(c, owner)["total"] == 1
