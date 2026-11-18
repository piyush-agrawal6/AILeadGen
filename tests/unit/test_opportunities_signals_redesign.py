"""Regression and functional tests for Opportunities & Signals Redesign."""
import json
import time
import uuid

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.organization import create_organization
from app.billing import subscription_access as access
from app.billing.subscription_schema import CONTRACT_SQL, EVENT_SQL
from app.database.prospects import now
from app.intent_radar import models as radar_models, service as radar_service
from app.platform.context import workspace_scope
from test_subscription_payment import accounts, customer  # noqa: F401


@pytest.fixture
def env_db(customer, monkeypatch):
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


def test_opportunities_listing_filters_sort_and_status_counts(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Opportunities Corp")
    org = w["organization_id"]
    _enable_workspace(c, org)
    stamp = now()

    # Seed 3 signals across different sources
    sig_gh = str(uuid.uuid4())
    sig_hn = str(uuid.uuid4())
    sig_yt = str(uuid.uuid4())
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Qualified',1,1)""",
        (sig_gh, org, "GitHub", "gh-10", "https://github.com/org/repo/issues/10", "Need enterprise webhook monitoring system", "Evaluating solutions for our team", stamp, stamp, "Recommendation request", 95, json.dumps({"provenance": {"retention_days": 30}})),
    )
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Qualified',1,1)""",
        (sig_hn, org, "Hacker News", "hn-20", "https://news.ycombinator.com/item?id=20", "Looking for B2B CRM replacement with API", "Our legacy CRM is failing", stamp, stamp, "Product comparison", 85, json.dumps({"provenance": {"retention_days": 30}})),
    )
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Qualified',1,1)""",
        (sig_yt, org, "YouTube", "yt-30", "https://youtube.com/watch?v=30", "How to track developer lead gen signals", "Exploring intent radar workflows", stamp, stamp, "Tool / service evaluation", 78, json.dumps({"provenance": {"retention_days": 30}})),
    )

    # Create 3 opportunities with distinct statuses, priorities and assignees
    opp1_id = str(uuid.uuid4())
    opp2_id = str(uuid.uuid4())
    opp3_id = str(uuid.uuid4())
    c.execute(
        """INSERT INTO intent_opportunities(id, organization_id, signal_id, status, priority, notes, next_action, assigned_to, created_by, created_at, updated_at)
           VALUES(?,?,?,'New','High','Webhook buyer ready to test','Book product demo',?,?,?,?)""",
        (opp1_id, org, sig_gh, owner, owner, stamp, stamp),
    )
    c.execute(
        """INSERT INTO intent_opportunities(id, organization_id, signal_id, status, priority, notes, next_action, assigned_to, created_by, created_at, updated_at)
           VALUES(?,?,?,'Reviewing','Medium','Reviewing CRM migration budget','Share pricing tier',NULL,?,?,?)""",
        (opp2_id, org, sig_hn, owner, stamp, stamp),
    )
    c.execute(
        """INSERT INTO intent_opportunities(id, organization_id, signal_id, status, priority, notes, next_action, assigned_to, created_by, created_at, updated_at)
           VALUES(?,?,?,'Qualified','Low','Saved YouTube leadgen study','Send documentation',?,?,?,?)""",
        (opp3_id, org, sig_yt, owner, owner, stamp, stamp),
    )

    with workspace_scope(c, owner, org):
        # 1. Total & status counts verification
        all_res = radar_service.listing(c, "opportunities", page=1, size=25)
        assert all_res["total"] == 3
        counts = all_res.get("status_counts")
        assert counts is not None
        assert counts["all"] == 3
        assert counts["new"] == 1
        assert counts["reviewing"] == 1
        assert counts["qualified"] == 1
        assert counts["dismissed"] == 0

        # 2. Filter by status
        rev_res = radar_service.listing(c, "opportunities", page=1, size=25, status="Reviewing")
        assert rev_res["total"] == 1
        assert rev_res["items"][0]["id"] == opp2_id

        # 3. Filter by priority
        high_res = radar_service.listing(c, "opportunities", page=1, size=25, priority="High")
        assert high_res["total"] == 1
        assert high_res["items"][0]["id"] == opp1_id

        # 4. Filter by source
        gh_res = radar_service.listing(c, "opportunities", page=1, size=25, source="GitHub")
        assert gh_res["total"] == 1
        assert gh_res["items"][0]["id"] == opp1_id

        # 5. Filter by assignee
        unassigned_res = radar_service.listing(c, "opportunities", page=1, size=25, assigned_to="unassigned")
        assert unassigned_res["total"] == 1
        assert unassigned_res["items"][0]["id"] == opp2_id

        # 6. Search across signal title & notes
        search_res = radar_service.listing(c, "opportunities", page=1, size=25, search="CRM")
        assert search_res["total"] == 1
        assert search_res["items"][0]["id"] == opp2_id


def test_opportunity_crud_duplicate_prevention_and_deletion(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Opp Lifecycle Org")
    org = w["organization_id"]
    _enable_workspace(c, org)
    stamp = now()

    sig_id = str(uuid.uuid4())
    c.execute(
        """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Qualified',1,1)""",
        (sig_id, org, "Hacker News", "hn-99", "https://news.ycombinator.com/item?id=99", "Looking for replacement data tool", "Evaluating alternatives", stamp, stamp, "Alternative search", 90, json.dumps({"provenance": {"retention_days": 30}})),
    )

    with workspace_scope(c, owner, org):
        # Create opportunity from signal
        created = radar_service.opportunity(c, sig_id, create_body=radar_models.OpportunityCreate(priority="High", notes="Urgent migration", next_action="Contact founder"))
        assert created["already_existed"] is False
        opp_id = created["id"]
        assert created["priority"] == "High"
        assert created["notes"] == "Urgent migration"

        # Duplicate creation returns existing record with already_existed=True
        duplicate = radar_service.opportunity(c, sig_id)
        assert duplicate["id"] == opp_id
        assert duplicate["already_existed"] is True

        # Fetch detail by key returns full signal attached
        detail = radar_service.get(c, "opportunities", opp_id)
        assert detail["id"] == opp_id
        assert detail["signal"]["id"] == sig_id
        assert detail["signal"]["title"] == "Looking for replacement data tool"

        # Update status, priority and notes
        updated = radar_service.opportunity(
            c,
            opp_id,
            body=radar_models.OpportunityUpdate(
                revision=detail["revision"],
                status="Reviewing",
                priority="Medium",
                notes="Budget confirmed",
                next_action="Send proposal",
                assigned_to=owner,
            ),
        )
        assert updated["status"] == "Reviewing"
        assert updated["priority"] == "Medium"
        assert updated["notes"] == "Budget confirmed"
        assert updated["assigned_to"] == owner

        # Delete opportunity removes it and logs audit record
        deleted = radar_service.delete_opportunity(c, opp_id)
        assert deleted["deleted"] is True
        assert deleted["id"] == opp_id

        # Listing no longer contains it
        after_del = radar_service.listing(c, "opportunities", page=1, size=25)
        assert after_del["total"] == 0


def test_signals_bulk_actions_support_reset_to_needs_review(env_db):
    c, _ = env_db
    owner = "owner@planebyte.com"
    w = create_organization(c, owner, "Bulk Action Org")
    org = w["organization_id"]
    _enable_workspace(c, org)
    stamp = now()

    # Seed 3 signals with 'Qualified' status
    sids = [str(uuid.uuid4()) for _ in range(3)]
    for idx, sid in enumerate(sids):
        c.execute(
            """INSERT INTO intent_signals(id, organization_id, source, source_record_id, source_url, title, excerpt, observed_at, retrieved_at, category, score, evidence_json, status, available, revision)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Qualified',1,1)""",
            (sid, org, "GitHub", f"gh-{idx}", f"https://github.com/org/repo/issues/{idx}", f"Discussion #{idx}", "Excerpt", stamp, stamp, "General discussion", 60, json.dumps({"provenance": {"retention_days": 30}})),
        )

    with workspace_scope(c, owner, org):
        # Bulk reset to Needs Review
        res = radar_service.bulk_action(c, radar_models.Bulk(ids=sids, action="needs_review"))
        assert res["updated"] == 3
        assert res["action"] == "needs_review"

        # Verify all signals in database have status 'Needs Review'
        rows = c.execute("SELECT status FROM intent_signals WHERE organization_id=?", (org,)).fetchall()
        assert all(r["status"] == "Needs Review" for r in rows)

        # Bulk mark reviewed
        res_rev = radar_service.bulk_action(c, radar_models.Bulk(ids=sids, action="review"))
        assert res_rev["updated"] == 3
        rows_rev = c.execute("SELECT status FROM intent_signals WHERE organization_id=?", (org,)).fetchall()
        assert all(r["status"] == "Reviewed" for r in rows_rev)
