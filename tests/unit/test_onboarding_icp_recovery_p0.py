"""Regression tests for P0 ICP setup allowance isolation and Skip/Resume onboarding."""
import json, time, uuid
import pytest
from fastapi import HTTPException
from app.billing import commercial_usage, subscription_access as access
from app.database.prospects import now
from app.intent_radar import permissions as radar_permissions
from app.platform import onboarding as setup
from app.platform.context import workspace_scope
from test_subscription_payment import subscribed, customer, accounts  # noqa: F401


def test_setup_jobs_use_isolated_setup_allowance_even_when_trial_ai_calls_are_exhausted(subscribed):
    c, s, org, actor, state, product, checkout, customer_data = subscribed
    # Simulate an active 3-day trial whose 3 product ai_calls are completely exhausted
    from app.billing import subscription_sync as sync
    sync.reconcile_subscription(state['id'], 'production')
    active = access.active(c, org)
    assert active is not None
    c.execute(
        "INSERT INTO subscription_usage(organization_id,contract_id,period_start,period_end,dimension,reserved,used) VALUES(?,?,?,?, 'ai_calls', 0, 3) "
        "ON CONFLICT(organization_id,contract_id,period_start,dimension) DO UPDATE SET used=3",
        (org, active['id'], active['paid_start'], active['paid_end']),
    )
    job_id = str(uuid.uuid4())
    stamp = now()
    c.execute(
        "INSERT INTO organization_profile_jobs(id,organization_id,created_by,request_id,website,status,created_at,updated_at,source_kind,use_ai) "
        "VALUES(?,?,?,?,?,'QUEUED',?,?,'ICP_RECOMMENDATIONS',1)",
        (job_id, org, actor, str(uuid.uuid4()), '', stamp, stamp),
    )
    c.commit()

    # Inside setup_scope, ICP generation MUST succeed via subscription_setup_usage (25 calls)
    # without hitting SETUP_LIMIT_EXHAUSTED on the 3-call product trial ledger!
    with workspace_scope(c, actor, org), access.setup_scope(c, job_id):
        assert commercial_usage.reserve(c, {'ai_calls': 1}, 'setup-icp:' + job_id) is True
        c.commit()

    # Product trial usage remains untouched at 3; isolated setup usage recorded 1
    prod_used = c.execute("SELECT used FROM subscription_usage WHERE organization_id=? AND dimension='ai_calls'", (org,)).fetchone()[0]
    setup_res = c.execute("SELECT reserved FROM subscription_setup_usage WHERE organization_id=? AND dimension='ai_calls'", (org,)).fetchone()[0]
    assert prod_used == 3
    assert setup_res == 1


def test_skip_onboarding_allows_entitled_dashboard_without_bypassing_payment(subscribed):
    c, s, org, actor, state, product, checkout, customer_data = subscribed
    # Before payment, skipping onboarding preserves IN_PROGRESS and NEVER unlocks unpaid Intent Radar
    with workspace_scope(c, actor, org):
        deferred = setup.set_deferred(c, True)
        assert deferred['status'] != 'COMPLETED'
        assert deferred['preferences']['setup_deferred'] is True
        c.commit()
        assert radar_permissions.availability(c, org)['enabled'] is False
        with pytest.raises(HTTPException) as denied:
            radar_permissions.context(c)
        assert denied.value.status_code == 402

    # Once a verified subscription/trial exists, deferred onboarding permits Intent Radar access
    from app.billing import subscription_sync as sync
    sync.reconcile_subscription(state['id'], 'production')
    with workspace_scope(c, actor, org):
        assert radar_permissions.availability(c, org)['enabled'] is True
        assert radar_permissions.context(c).organization_id == org
        resumed = setup.set_deferred(c, False)
        assert resumed['preferences']['setup_deferred'] is False
        c.commit()
        assert radar_permissions.availability(c, org)['enabled'] is False
