"""Verified, fixed-term access and trial isolation over the shared quota ledger.

No public function in this module creates a paid period. Payment fulfillment must
persist independently verified order evidence first. Expiry preserves history.
"""
import json
import time
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config.settings import get_settings


def enabled():
    return get_settings().heysow_access_periods_enabled


def managed(c, org):
    return bool(enabled() and c.execute('SELECT 1 FROM customer_workspace_access WHERE organization_id=?', (org,)).fetchone())


def ledgers(c, org):
    from app.billing.subscription_access import in_setup,has_contract
    if in_setup(org):return ('subscription_setup_usage','subscription_setup_reservations')
    if has_contract(c,org):return ('subscription_usage','subscription_reservations')
    # Identifiers are fixed internally; caller input never selects a table.
    return ('access_period_usage', 'access_period_reservations') if managed(c, org) else ('commercial_usage', 'commercial_reservations')


def active(c, org):
    if not managed(c, org):
        return None
    s = get_settings()
    stamp = int(time.time())
    rows = c.execute("""SELECT p.* FROM access_periods p
        WHERE p.organization_id=? AND p.status='ACTIVE' AND p.verified_at IS NOT NULL
        AND p.paid_start<=? AND p.paid_end>? ORDER BY p.paid_start,p.id LIMIT 2""", (org, stamp, stamp)).fetchall()
    if len(rows) > 1:
        raise HTTPException(503, 'Workspace access periods require administrator review.')
    if not rows:
        return None
    row = dict(rows[0])
    if row['source_kind'] == 'TRIAL':
        claim = c.execute('SELECT t.* FROM launch_trial_claims t JOIN customer_workspace_access w ON w.organization_id=t.organization_id AND w.registered_by=t.user_id WHERE t.id=? AND t.organization_id=?', (row['source_id'], org)).fetchone()
        from app.billing.trials import POLICY
        saved = json.loads(row['plan_json'])
        if not claim or row['mode'] != 'trial' or row['plan_code'] != 'trial' or saved.get('limits') != POLICY['limits'] or saved.get('version') != claim['policy_version'] or row['paid_end'] - row['paid_start'] != POLICY['duration_days'] * 86400:
            raise HTTPException(503, 'The saved trial policy requires administrator review.')
    else:
        return None  # Historical orders are readable, never a commercial grant.
    from app.billing.contracts import snapshot
    snapshot(row)
    # Compatibility for existing customer usage summaries; snapshots stay fixed.
    row['catalog_version'] = json.loads(row['plan_json']).get('version', '')
    return row


def require_current(c, org):
    from app.billing.subscription_access import required,require_product,active as recurring
    if required(c,org):return require_product(c,org)
    value=recurring(c,org)
    if value:return value
    if not managed(c, org):
        return None
    row = active(c, org)
    if not row:
        raise HTTPException(402, {'code': 'ACCESS_EXPIRED', 'message': 'Workspace access has expired or has not started. Saved research remains available. Review billing to renew access.'})
    return row


def require_paid_feature(c, org, dimension):
    row = require_current(c, org)
    if row and json.loads(row['plan_json'])['limits'][dimension] <= 0:
        raise HTTPException(403, {'code': 'PAID_PLAN_REQUIRED', 'message': dimension.replace('_', ' ').capitalize() + ' requires a paid plan. Your saved records remain available.'})
    return row


def next_period(c, org, plan_code, interval, *, stamp=None):
    """Owner-approved durations; future renewals cannot overlap or change early."""
    if interval not in ('monthly', 'yearly'):
        raise ValueError('Unknown access interval.')
    stamp = int(time.time()) if stamp is None else stamp
    rows = c.execute("SELECT plan_code,paid_end FROM access_periods WHERE organization_id=? AND source_kind='PAYMENT' AND status='ACTIVE' AND paid_end>? ORDER BY paid_end DESC LIMIT 1", (org, stamp)).fetchall()
    # A different plan is queued after the last verified paid period. It never
    # changes the currently active plan or creates overlapping access.
    start = rows[0]['paid_end'] if rows else stamp
    if interval == 'monthly':
        end = start + 30 * 86400
    else:
        at = datetime.fromtimestamp(start, timezone.utc)
        try:
            end = int(at.replace(year=at.year + 1).timestamp())
        except ValueError:  # February 29 renews on February 28 next year.
            end = int(at.replace(year=at.year + 1, day=28).timestamp())
    return start, end


def scheduled_sql(org):
    if org not in ('m.organization_id', 'j.organization_id'):
        raise ValueError('Internal scheduler alias required.')
    if not enabled():
        return '1=1', []
    s=get_settings()
    sql='NOT EXISTS(SELECT 1 FROM customer_workspace_access w WHERE w.organization_id='+org+')';args=[]
    if s.subscription_onboarding_required:
        from app.billing.subscription_access import scheduled_sql as recurring
        extra,values=recurring(org)
        return '('+sql+' OR '+extra+')',args+values
    return sql,args


def notification_authorized(c, row):
    """Private outbox messages require a retained, matching domain record."""
    org = row['organization_id']
    if not org:
        return False
    from app.api.organization import membership_role
    if membership_role(c, row['account_email'], org)!='OWNER':
        return False
    purpose = row['purpose']
    if purpose == 'PAYMENT_CONFIRMED':
        return bool(c.execute("SELECT 1 FROM payu_access_orders WHERE id=? AND organization_id=? AND created_by=? AND status='PAID' AND verified_at IS NOT NULL AND provider_payment_id IS NOT NULL", (row['authority_id'], org, row['account_email'])).fetchone())
    if purpose in ('RENEWAL_REMINDER', 'ACCESS_EXPIRED'):
        period = c.execute("SELECT paid_end FROM access_periods WHERE id=? AND organization_id=? AND source_kind='PAYMENT' AND status IN ('ACTIVE','EXPIRED')", (row['authority_id'], org)).fetchone()
        if not period:
            return False
        remaining = period['paid_end'] - int(time.time())
        return remaining <= 0 if purpose == 'ACCESS_EXPIRED' else 0 < remaining <= 3 * 86400
    # Workspace notices need an explicit enabled subscription and persisted
    # recipient preference before delivery is implemented; no generic sender.
    return False
