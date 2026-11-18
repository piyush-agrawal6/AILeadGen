"""Regression tests for Settings 3.0, Multi-Workspace Isolation & Access, and Global Search 2.0."""
import json
import uuid
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.organization import create_organization, membership_role
from app.billing import subscription_access as access, subscriptions as sub_service
from app.database.prospects import now
from app.billing.subscription_schema import EVENT_SQL, CONTRACT_SQL
from app.intent_radar import models as radar_models, permissions as radar_perms, service as radar_service
from app.notifications import center as notif_center
from app.platform import company_profiles, memberships, workspaces
from app.platform.context import workspace_scope
from app.platform.workspace_search import search_workspace
from test_subscription_payment import customer, accounts  # noqa: F401


@pytest.fixture
def isolated_db(customer, monkeypatch):
    c, s = customer
    c.executescript(EVENT_SQL + CONTRACT_SQL)
    c.commit()
    monkeypatch.setattr(s, "heysow_workspace_management_enabled", True)
    monkeypatch.setattr(s, "subscription_onboarding_required", True)
    monkeypatch.setattr(s, "subscription_terms_version", access.POLICY)
    monkeypatch.setattr(s, "creem_environment", "production")
    monkeypatch.setattr(s, "creem_api_key", SecretStr("synthetic"))
    monkeypatch.setattr(s, "intent_radar_stage", "Beta")
    monkeypatch.setattr(s, "intent_radar_growth_enabled", True)
    monkeypatch.setattr(s, "allowed_user_emails", "owner@planebyte.com,member@planebyte.com")
    return c, s


def test_secondary_workspace_isolation_and_creem_grant_without_manual_grant(isolated_db):
    c, _ = isolated_db
    owner = "owner@planebyte.com"

    # Workspace 1 (PlaneByte) with manual grant + completed onboarding
    w1 = create_organization(c, owner, "PlaneByte")
    org1 = w1["organization_id"]
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org1,))
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org1,))
    c.execute("DELETE FROM subscription_requirements WHERE organization_id=?", (org1,))

    # Workspace 2 (Syntaxwars) created by same owner
    res2 = workspaces.create_workspace(
        c,
        owner,
        workspaces.WorkspaceCreate(name="Syntaxwars", request_id=uuid.uuid4()),
    )
    org2 = str(res2["organization_id"])
    assert org2 != org1

    # PlaneByte stays enabled; Syntaxwars MUST NOT inherit PlaneByte's access
    assert radar_perms.availability(c, org1)["enabled"] is True
    avail2 = radar_perms.availability(c, org2)
    assert avail2["enabled"] is False
    assert avail2["access_state"] == "SETUP_REQUIRED"
    assert access.required(c, org2) is True

    # Completing onboarding without verified subscription yields actionable activation state (never bypasses payment!)
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org2,))
    with workspace_scope(c, owner, org2):
        avail2_after_setup = radar_perms.availability(c, org2)
        assert avail2_after_setup["enabled"] is False
        assert avail2_after_setup["access_state"] in ("TRIAL_AVAILABLE", "SUBSCRIPTION_REQUIRED")

    # Once a verified Creem contract + payment exists for Syntaxwars, access unlocks even with manual_grant=0!
    import time
    ts = int(time.time())
    contract_id = str(uuid.uuid4())
    checkout_id = str(uuid.uuid4())
    plan_json = json.dumps({"code": "starter", "name": "Starter", "monthly_minor": 5900, "limits": {"searches": 100, "ai_calls": 20, "ai_tokens": 500000, "monitors": 2, "monitor_executions": 60, "reports": 5, "team_members": 1, "api_requests": 0, "monitor_interval_hours": 24}})
    c.execute(
        """INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at)
           VALUES(?,?,?,'creem','production','starter','paid',?,'hash','cust_syn','prod_syn','COMPLETED','US','USD',5900,0,?,?,'{}',?,?)""",
        (checkout_id, org2, owner, str(uuid.uuid4()), access.POLICY, now(), now(), now()),
    )
    c.execute(
        """INSERT INTO subscription_contracts(id,organization_id,created_by,provider,environment,provider_id,customer_id,checkout_id,plan_code,plan_json,status,recurring_authorized,period_start,period_end,verified_at,evidence_json,created_at,updated_at)
           VALUES(?,?,?,'creem','production','sub_syn','cust_syn',?,'starter',?,'active',1,?,?,?,'{}',?,?)""",
        (contract_id, org2, owner, checkout_id, plan_json, ts - 60, ts + 86400, now(), now(), now()),
    )
    c.execute("INSERT INTO subscription_workspace_slots(organization_id,environment,contract_id) VALUES(?,'production',?)", (org2, contract_id))
    c.execute(
        "INSERT INTO subscription_payments(provider,environment,payment_id,organization_id,contract_id,amount_minor,currency,status,period_start,period_end,evidence_json,recorded_at) VALUES('creem','production','tran_syn',?,?,5900,'USD','paid',?,?,'{}',?)",
        (org2, contract_id, ts - 60, ts + 86400, now()),
    )
    avail2_paid = radar_perms.availability(c, org2)
    assert avail2_paid["enabled"] is True
    assert avail2_paid["access_state"] == "ACTIVE"


def test_workspace_rename_leave_and_last_owner_protection(isolated_db):
    c, _ = isolated_db
    owner = "owner@planebyte.com"
    member = "member@planebyte.com"
    w = create_organization(c, owner, "Alpha Org")
    org = w["organization_id"]

    # Last owner cannot leave
    with pytest.raises(HTTPException) as exc:
        workspaces.leave_workspace(c, owner, org)
    assert exc.value.status_code == 409

    # Owner can rename
    renamed = workspaces.rename_workspace(c, owner, org, workspaces.WorkspaceRename(name="Beta Org"))
    assert renamed["name"] == "Beta Org"

    # Non-owner cannot rename
    from app.api.organization import ensure_user
    ensure_user(c, member)
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,'MEMBER','ACTIVE',?,?)", (str(uuid.uuid4()), org, member, now(), now()))
    with pytest.raises(HTTPException) as exc2:
        workspaces.rename_workspace(c, member, org, workspaces.WorkspaceRename(name="Hacked"))
    assert exc2.value.status_code == 403

    # Member can leave cleanly
    left = workspaces.leave_workspace(c, member, org)
    assert left["left"] is True
    assert membership_role(c, member, org) is None


def test_preferences_notification_isolation_and_ceiling_enforcement(isolated_db):
    c, s = isolated_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Prefs Org")
    org = w["organization_id"]
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org,))
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
    c.execute("DELETE FROM subscription_requirements WHERE organization_id=?", (org,))

    with workspace_scope(c, owner, org):
        # Save personal notification preferences first
        notif_center.update_preferences(
            c,
            notif_center.NotificationPreferencesUpdate(
                in_app_enabled=True,
                email_enabled=True,
                email_cadence="immediate",
                timezone="UTC",
                quiet_hours_enabled=True,
                quiet_hours_start="23:00",
                quiet_hours_end="06:00",
                categories={"discovery": True, "signals": False, "security": False, "billing": False},
            ),
        )
        # GET /intent-radar/settings must NOT leak user_notification_preferences & must include limits_meta
        prefs = radar_service.preferences(c)
        assert "user_notification_preferences" not in prefs
        assert "limits_meta" in prefs
        assert prefs["limits_meta"]["platform_daily_call_limit"] == s.intent_radar_ai_daily_calls

        # Saving workspace Research Preferences succeeds without 422 or 409, AND preserves user notification prefs!
        body = radar_models.Preferences(
            source_retention_days=30,
            default_view="cards",
            min_relevance=55,
            ai_assistance=True,
            analysis_daily_call_limit=min(3, s.intent_radar_ai_daily_calls),
            analysis_daily_token_limit=min(50000, s.intent_radar_ai_daily_tokens),
            topics=["webhooks"],
            alerts_enabled=True,
            alert_threshold=80,
            revision=prefs["revision"],
        )
        saved = radar_service.preferences(c, body)
        assert saved["default_view"] == "cards"
        assert saved["min_relevance"] == 55
        # Personal notification prefs still preserved with mandatory security/billing forced True!
        np = notif_center.get_preferences(c)
        assert np["categories"]["signals"] is False
        assert np["categories"]["security"] is True
        assert np["categories"]["billing"] is True

        # Exceeding platform ceiling is rejected with 422
        with pytest.raises(HTTPException) as exc:
            radar_service.preferences(
                c,
                radar_models.Preferences(
                    analysis_daily_token_limit=s.intent_radar_ai_daily_tokens + 10000,
                    revision=saved["revision"],
                ),
            )
        assert exc.value.status_code == 422


def test_profile_quality_and_workspace_search_isolation(isolated_db):
    c, _ = isolated_db
    owner = "owner@planebyte.com"
    w1 = create_organization(c, owner, "PlaneByte")
    w2 = create_organization(c, owner, "Syntaxwars")
    org1, org2 = w1["organization_id"], w2["organization_id"]
    for org in (org1, org2):
        c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org,))
        c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
        c.execute("DELETE FROM subscription_requirements WHERE organization_id=?", (org,))

    # Profile quality flags bad placeholders without mutating stored data
    issues = company_profiles.analyze_profile_quality({
        "website": "https://example.com",
        "industry": "asdf",
        "description": "test",
        "positioning": "lorem ipsum",
        "countries_served": ["US"],
        "target_customers": ["foo"],
        "target_industries": [],
        "specialties": [],
        "products_services": [{"name": "Demo", "category": "", "description": "sample"}],
    })
    codes = {i["code"] for i in issues}
    assert "invalid_industry" in codes
    assert "low_quality_description" in codes
    assert "placeholder_website" in codes

    # Insert isolated monitor & signal in org1 only
    c.execute(
        "INSERT INTO intent_monitors(id,organization_id,created_by,name,description,goal,configuration_json,status,request_id,fingerprint,revision,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'Active',?,?,1,?,?)",
        (str(uuid.uuid4()), org1, owner, "PlaneByte Webhook Tracker", "Track webhook bugs", "", json.dumps({"keywords": ["webhook"]}), str(uuid.uuid4()), "fp-1", now(), now()),
    )
    # Search in org1 finds it
    with workspace_scope(c, owner, org1):
        res1 = search_workspace(c, organization_id=org1, actor=owner, query="Webhook Tracker")
        assert any("Webhook Tracker" in m["title"] for m in res1["groups"]["monitors"])

    # Search in org2 MUST NEVER see org1's monitor
    with workspace_scope(c, owner, org2):
        res2 = search_workspace(c, organization_id=org2, actor=owner, query="Webhook Tracker")
        assert len(res2["groups"]["monitors"]) == 0
