"""Tests for Starter Trial vs Paid Starter distinction and secure temporary internal testing allowance."""
import json
import time
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.billing import (
    access_periods,
    commercial,
    commercial_usage,
    contracts,
    creem,
    overview as billing_overview,
    subscription_access as access,
    subscription_sync as sync,
    subscriptions as service,
)
from app.billing.subscription_schema import CONTRACT_SQL, EVENT_SQL
from app.database.prospects import now
from app.platform.context import workspace_scope
from test_customer_accounts import accounts, customer, signup, verified


def iso(stamp: int) -> str:
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat()


def _setup_workspace_checkout(c, s, *, email='owner@planebyte.com', plan_code='starter', variant='trial'):
    result, _ = verified(c, signup(email=email))
    org = result['organization_id']
    stamp = int(time.time())
    suffix = uuid.uuid4().hex[:10]
    provider_id = f'sub_{suffix}'
    customer_id = f'cust_{suffix}'
    product_id = f'prod_{suffix}'
    checkout_id = f'ch_{suffix}'
    key = str(uuid.uuid4())
    c.execute(
        "INSERT INTO subscription_billing_profiles(organization_id,country,status,verification_source,verification_reference,verified_at,updated_at) VALUES(?,'IN','VERIFIED','CREEM_API',?,?,?)",
        (org, customer_id, now(), now()),
    )
    c.execute(
        "INSERT INTO subscription_customers(provider,environment,organization_id,customer_id,created_at) VALUES('creem','production',?,?,?)",
        (org, customer_id, now()),
    )
    c.execute(
        "INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,provider_checkout_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at) VALUES(?,?,?,'creem','production',?,?,?,?,?,?,?,'PENDING','IN','USD',5900,?,?,?,?,?,?)",
        (
            key,
            org,
            email,
            plan_code,
            variant,
            str(uuid.uuid4()),
            'hash-' + suffix,
            customer_id,
            product_id,
            checkout_id,
            3 if variant == 'trial' else 0,
            access.POLICY,
            now(),
            '{}',
            now(),
            now(),
        ),
    )
    c.commit()
    return {
        'org': org,
        'email': email,
        'stamp': stamp,
        'provider_id': provider_id,
        'customer_id': customer_id,
        'product_id': product_id,
        'checkout_id': checkout_id,
        'key': key,
    }


def _reconcile_trial(monkeypatch, info, *, status='trialing'):
    stamp = info['stamp']
    trial_end = stamp + access.TRIAL_SECONDS
    state = {
        'id': info['provider_id'],
        'mode': 'prod',
        'status': status,
        'collection_method': 'charge_automatically',
        'product': info['product_id'],
        'customer': info['customer_id'],
        'current_period_start_date': iso(stamp),
        'current_period_end_date': iso(trial_end),
        'next_transaction_date': None if status in ('canceled', 'scheduled_cancel') else iso(trial_end),
        'updated_at': iso(stamp + 10),
        'created_at': iso(stamp),
    }
    product = {
        'id': info['product_id'],
        'mode': 'prod',
        'price': 5900,
        'currency': 'USD',
        'billing_type': 'recurring',
        'billing_period': 'every-month',
        'trial_period_days': 3,
        'trial_price': 0,
        'tax_mode': 'inclusive',
    }
    checkout = {
        'id': info['checkout_id'],
        'mode': 'prod',
        'status': 'completed',
        'request_id': info['key'],
        'subscription': info['provider_id'],
        'customer': info['customer_id'],
        'product': info['product_id'],
    }
    customer_data = {
        'id': info['customer_id'],
        'mode': 'prod',
        'email': info['email'],
        'external_id': info['org'],
        'country': 'IN',
    }
    monkeypatch.setattr(creem, 'get_subscription', lambda *a, **kw: dict(state))
    monkeypatch.setattr(creem, 'get_product', lambda *a, **kw: dict(product))
    monkeypatch.setattr(creem, 'get_checkout', lambda *a, **kw: dict(checkout))
    monkeypatch.setattr(creem, 'get_customer', lambda *a, **kw: dict(customer_data))
    return sync.reconcile_subscription(info['provider_id'], 'production')


def _reconcile_paid_starter(monkeypatch, info):
    stamp = info['stamp']
    period_end = stamp + 2678400
    state = {
        'id': info['provider_id'],
        'mode': 'prod',
        'status': 'active',
        'collection_method': 'charge_automatically',
        'product': info['product_id'],
        'customer': info['customer_id'],
        'last_transaction_id': 'tran_' + info['provider_id'][4:],
        'current_period_start_date': iso(stamp),
        'current_period_end_date': iso(period_end),
        'next_transaction_date': iso(period_end),
        'updated_at': iso(stamp + 10),
        'created_at': iso(stamp),
    }
    product = {
        'id': info['product_id'],
        'mode': 'prod',
        'price': 5900,
        'currency': 'USD',
        'billing_type': 'recurring',
        'billing_period': 'every-month',
        'trial_period_days': 0,
        'trial_price': 0,
        'tax_mode': 'inclusive',
    }
    checkout = {
        'id': info['checkout_id'],
        'mode': 'prod',
        'status': 'completed',
        'request_id': info['key'],
        'subscription': info['provider_id'],
        'customer': info['customer_id'],
        'product': info['product_id'],
    }
    customer_data = {
        'id': info['customer_id'],
        'mode': 'prod',
        'email': info['email'],
        'external_id': info['org'],
        'country': 'IN',
    }
    txn = {
        'id': state['last_transaction_id'],
        'mode': 'prod',
        'subscription': info['provider_id'],
        'customer': info['customer_id'],
        'currency': 'USD',
        'amount_paid': 5900,
        'status': 'paid',
        'period_start': stamp,
        'period_end': period_end,
    }
    monkeypatch.setattr(creem, 'get_subscription', lambda *a, **kw: dict(state))
    monkeypatch.setattr(creem, 'get_product', lambda *a, **kw: dict(product))
    monkeypatch.setattr(creem, 'get_checkout', lambda *a, **kw: dict(checkout))
    monkeypatch.setattr(creem, 'get_customer', lambda *a, **kw: dict(customer_data))
    monkeypatch.setattr(creem, 'get_transaction', lambda *a, **kw: dict(txn))
    return sync.reconcile_subscription(info['provider_id'], 'production')


@pytest.fixture
def env(customer, monkeypatch):
    c, s = customer
    c.executescript(EVENT_SQL + CONTRACT_SQL)
    c.commit()
    for k, v in {
        'subscription_onboarding_required': True,
        'subscription_checkout_enabled': True,
        'subscription_terms_version': access.POLICY,
        'creem_environment': 'production',
        'creem_api_key': SecretStr('synthetic'),
        'intent_radar_stage': 'Beta',
        'intent_radar_growth_enabled': True,
        'internal_testing_workspace_id': '',
        'internal_testing_owner_email': '',
        'internal_testing_expires_at': 0,
    }.items():
        monkeypatch.setattr(s, k, v)
    return c, s


def test_starter_trial_and_paid_starter_labels_and_limits_are_distinct(env, monkeypatch):
    c, s = env
    trial_ws = _setup_workspace_checkout(c, s, email='contact@planebyte.com', plan_code='starter', variant='trial')
    paid_ws = _setup_workspace_checkout(c, s, email='buyer@acme-corp.com', plan_code='starter', variant='paid')

    with workspace_scope(c, trial_ws['email'], trial_ws['org']):
        _reconcile_trial(monkeypatch, trial_ws, status='canceled')
        sub_summary = service.summary(c)
        assert sub_summary['active'] is True
        assert sub_summary['contract']['is_trial'] is True
        assert sub_summary['contract']['entitlement_label'] == 'Starter Trial'
        assert sub_summary['contract']['status'] == 'canceled'
        assert sub_summary['contract']['cancel_confirmed_at'] is not None

        ov = billing_overview.overview(c)
        assert ov['access']['kind'] == 'Starter Trial'
        assert ov['access']['is_trial'] is True
        assert ov['access']['commercial_subscription'] is False
        assert ov['subscription']['entitlement_label'] == 'Starter Trial'
        assert ov['subscription']['is_trial'] is True
        assert 'internal_testing' not in ov

        # Exact trial limits enforced: 5 searches, 3 AI calls, 1 monitor, 0 reports
        assert commercial_usage.reserve(c, {'searches': 5, 'ai_calls': 3}, 'trial-use-all')
        c.commit()
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'searches': 1}, 'trial-sixth-search')
        assert exc.value.status_code == 429
        c.rollback()
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'ai_calls': 1}, 'trial-fourth-ai')
        assert exc.value.status_code == 429
        c.rollback()
        with pytest.raises(HTTPException) as exc:
            commercial_usage.capacity(c, trial_ws['org'], 'monitors', 1)
        assert exc.value.status_code == 429
        c.rollback()
        with pytest.raises(HTTPException) as exc:
            access_periods.require_paid_feature(c, trial_ws['org'], 'reports')
        assert exc.value.status_code == 403
        c.rollback()

    with workspace_scope(c, paid_ws['email'], paid_ws['org']):
        _reconcile_paid_starter(monkeypatch, paid_ws)
        sub_summary = service.summary(c)
        assert sub_summary['active'] is True
        assert sub_summary['contract']['is_trial'] is False
        assert sub_summary['contract']['entitlement_label'] == 'Paid Starter'

        ov = billing_overview.overview(c)
        assert ov['access']['kind'] == 'Paid Starter'
        assert ov['access']['is_trial'] is False
        assert ov['access']['commercial_subscription'] is True
        assert ov['subscription']['entitlement_label'] == 'Paid Starter'
        assert ov['subscription']['is_trial'] is False
        assert 'internal_testing' not in ov

        # Exact Paid Starter limits: 100 searches, 20 AI calls, 5 reports, 2 monitors
        assert commercial_usage.reserve(c, {'searches': 100, 'ai_calls': 20, 'reports': 5}, 'paid-use-all')
        c.commit()
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'searches': 1}, 'paid-over-100')
        assert exc.value.status_code == 429
        assert commercial_usage.capacity(c, paid_ws['org'], 'monitors', 1) is True
        with pytest.raises(HTTPException) as exc:
            commercial_usage.capacity(c, paid_ws['org'], 'monitors', 2)
        assert exc.value.status_code == 429


def test_internal_testing_never_bypasses_payment_or_leaks_to_regular_customers(env, monkeypatch):
    c, s = env
    unpaid_ws = _setup_workspace_checkout(c, s, email='unpaid@planebyte.com', plan_code='starter', variant='trial')
    customer_ws = _setup_workspace_checkout(c, s, email='alice@customer.io', plan_code='starter', variant='trial')

    future = int(time.time()) + 3600
    monkeypatch.setattr(s, 'internal_testing_workspace_id', unpaid_ws['org'])
    monkeypatch.setattr(s, 'internal_testing_owner_email', unpaid_ws['email'])
    monkeypatch.setattr(s, 'internal_testing_expires_at', future)

    # Unpaid workspace MUST STILL fail closed with 402 PAYMENT_REQUIRED
    with workspace_scope(c, unpaid_ws['email'], unpaid_ws['org']):
        assert access.active(c, unpaid_ws['org']) is None
        with pytest.raises(HTTPException) as denied:
            access.require_product(c, unpaid_ws['org'])
        assert denied.value.status_code == 402

    # Regular customer workspace NEVER receives internal testing allowance
    with workspace_scope(c, customer_ws['email'], customer_ws['org']):
        _reconcile_trial(monkeypatch, customer_ws, status='trialing')
        ov = billing_overview.overview(c)
        assert ov['access']['kind'] == 'Starter Trial'
        assert 'internal_testing' not in ov
        limits = contracts.snapshot(contracts.active(c, customer_ws['org']))['limits']
        assert limits == access.TRIAL_LIMITS


def test_internal_testing_preserves_trial_history_audits_usage_and_auto_expires(env, monkeypatch):
    c, s = env
    owner_ws = _setup_workspace_checkout(c, s, email='contact@planebyte.com', plan_code='starter', variant='trial')

    with workspace_scope(c, owner_ws['email'], owner_ws['org']):
        contract = _reconcile_trial(monkeypatch, owner_ws, status='canceled')
        trial_start = contract['period_start']
        trial_end = contract['period_end']

        # Exhaust original Starter Trial limits first
        commercial_usage.reserve(c, {'searches': 5, 'ai_calls': 3}, 'orig-trial-usage')
        commercial_usage.settle(c, 'orig-trial-usage')
        c.commit()
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'searches': 1}, 'blocked-before-override')
        assert exc.value.status_code == 429
        c.rollback()

        # Enable temporary bounded internal testing allowance (48h, well inside 72h trial)
        override_expiry = trial_start + 48 * 3600
        monkeypatch.setattr(s, 'internal_testing_workspace_id', owner_ws['org'])
        monkeypatch.setattr(s, 'internal_testing_owner_email', owner_ws['email'])
        monkeypatch.setattr(s, 'internal_testing_expires_at', override_expiry)
        monkeypatch.setattr(s, 'internal_testing_searches_limit', 25)
        monkeypatch.setattr(s, 'internal_testing_ai_calls_limit', 12)
        monkeypatch.setattr(s, 'internal_testing_monitors_limit', 5)

        # Wrong owner email must fail closed
        monkeypatch.setattr(s, 'internal_testing_owner_email', 'someone-else@planebyte.com')
        assert access.active(c, owner_ws['org'])['internal_testing'] is None
        monkeypatch.setattr(s, 'internal_testing_owner_email', owner_ws['email'])

        # Excessive window (>7 days) must fail closed
        monkeypatch.setattr(s, 'internal_testing_expires_at', int(time.time()) + 8 * 86400)
        assert access.active(c, owner_ws['org'])['internal_testing'] is None
        monkeypatch.setattr(s, 'internal_testing_expires_at', override_expiry)

        # Active internal testing allowance works within bounds
        ov = billing_overview.overview(c)
        assert ov['access']['kind'] == 'Starter Trial'
        assert ov['access']['is_trial'] is True
        assert ov['internal_testing']['active'] is True
        assert ov['internal_testing']['expires_at'] == override_expiry
        assert ov['internal_testing']['base_usage']['searches'] == 5
        assert ov['internal_testing']['base_usage']['ai_calls'] == 3

        # Run bounded searches & AI operations + monitor check under internal testing
        assert commercial_usage.reserve(c, {'searches': 10, 'ai_calls': 5}, 'internal-test-op-1')
        assert commercial_usage.capacity(c, owner_ws['org'], 'monitors', 3) is True
        c.commit()

        # Still strictly bounded — exceeding internal testing cap returns 429
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'searches': 16}, 'internal-test-over-cap')
        assert exc.value.status_code == 429
        c.rollback()

        # Audit log recorded every internal testing operation
        audits = c.execute(
            "SELECT action, entity, details_json FROM audit_log WHERE organization_id=? AND action='INTERNAL_TESTING_ALLOWANCE_USED'",
            (owner_ws['org'],),
        ).fetchall()
        assert len(audits) >= 2
        assert any(json.loads(r['details_json'])['operation_id'] == 'internal-test-op-1' for r in audits)

        # Original Creem contract, trial claim, payments, and trial usage rows are 100% untouched!
        orig_contract = c.execute('SELECT status, period_start, period_end, cancel_confirmed_at FROM subscription_contracts WHERE id=?', (contract['id'],)).fetchone()
        assert orig_contract['status'] == 'canceled'
        assert orig_contract['period_start'] == trial_start
        assert orig_contract['period_end'] == trial_end
        assert orig_contract['cancel_confirmed_at'] is not None
        assert c.execute('SELECT COUNT(*) FROM subscription_payments WHERE organization_id=?', (owner_ws['org'],)).fetchone()[0] == 0
        orig_usage = {
            r['dimension']: (r['used'], r['reserved'])
            for r in c.execute(
                'SELECT dimension, used, reserved FROM subscription_usage WHERE organization_id=? AND contract_id=? AND period_start=?',
                (owner_ws['org'], contract['id'], trial_start),
            ).fetchall()
        }
        assert orig_usage == {'searches': (5, 0), 'ai_calls': (3, 0)}

        # Auto-expiry: advance time past override_expiry (while trial is still active!)
        monkeypatch.setattr(access.time, 'time', lambda: override_expiry + 5)
        expired_active = access.active(c, owner_ws['org'])
        assert expired_active is not None
        assert expired_active['internal_testing'] is None
        assert contracts.snapshot(expired_active)['limits'] == access.TRIAL_LIMITS

        ov_after = billing_overview.overview(c)
        assert 'internal_testing' not in ov_after
        assert ov_after['access']['kind'] == 'Starter Trial'

        # Immediately snaps back to preserved 5/5 trial usage -> new search blocked with 429
        with pytest.raises(HTTPException) as exc:
            commercial_usage.reserve(c, {'searches': 1}, 'blocked-after-expiry')
        assert exc.value.status_code == 429
        c.rollback()

        # In-flight reservation from before expiry still settles cleanly without mutating original trial rows!
        assert commercial_usage.settle(c, 'internal-test-op-1') is True
        c.commit()
        orig_usage_after = {
            r['dimension']: (r['used'], r['reserved'])
            for r in c.execute(
                'SELECT dimension, used, reserved FROM subscription_usage WHERE organization_id=? AND contract_id=? AND period_start=?',
                (owner_ws['org'], contract['id'], trial_start),
            ).fetchall()
        }
        assert orig_usage_after == {'searches': (5, 0), 'ai_calls': (3, 0)}
