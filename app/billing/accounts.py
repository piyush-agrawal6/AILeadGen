"""Explicit billing links. An account anchor is never a research/resource authorization context."""
import json,uuid
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.api.organization import membership_role
from app.developer.keys import lock

PILOT_ACCOUNT='e3c5d319-0896-4772-9dc8-227c9b0b3edd'
PILOT_CHILD='835e301d-271b-45d4-aac7-d8b8675614b9'

def pilot():return get_settings().shared_billing_owner_pilot

def enabled(org=None):
    s=get_settings()
    # In production the master switch alone must never enable general sharing.
    return s.shared_billing_accounts_enabled and (s.app_env!='production' or pilot()) and (not pilot() or org is None or org in (PILOT_ACCOUNT,PILOT_CHILD))

def anchor(c,org):
    if not enabled(org) or not org:return org
    row=c.execute('SELECT account_id FROM billing_workspace_links WHERE workspace_id=?',(org,)).fetchone()
    if not row:raise HTTPException(409,'Workspace billing association requires reconciliation.')
    if pilot() and row[0]!=org and (row[0],org)!=(PILOT_ACCOUNT,PILOT_CHILD):raise HTTPException(409,'Billing association is outside the authorized pilot.')
    return row[0]

def admin(c,account,actor):
    return membership_role(c,actor,account)=='OWNER' and bool(c.execute('SELECT 1 FROM billing_account_admins WHERE account_id=? AND user_id=?',(account,actor)).fetchone())

def guard_purchase(c,org,actor):
    """Financial mutations fail closed for attached workspaces even during flag rollback."""
    if not enabled():
        head=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
        if head<(1016 if head>=1000 else 58):return
    link=c.execute('SELECT account_id FROM billing_workspace_links WHERE workspace_id=?',(org,)).fetchone()
    if not link or link[0]!=org:raise HTTPException(409,'Manage the existing subscription from the billing account’s primary workspace.')
    if enabled(org) and not admin(c,org,actor):raise HTTPException(403,'Billing account administrator required.')

def register(c,workspace,actor,account=None):
    head=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
    if head<(1016 if head>=1000 else 58):
        if account is not None:raise HTTPException(503,'Shared billing requires the account schema upgrade.')
        return  # Independent pre-upgrade workspace; migration backfills its own account.
    stamp=now()
    if account is None:
        account=workspace;c.execute('INSERT INTO workspace_billing_accounts(id,created_at) VALUES(?,?)',(account,stamp));c.execute('INSERT INTO billing_account_admins(account_id,user_id) VALUES(?,?)',(account,actor))
    else:
        lock(c,account)
        if pilot() or not enabled(account) or not admin(c,account,actor):raise HTTPException(403,'This account cannot be selected for new shared workspaces.')
        check_relationships(c,account)
    c.execute('INSERT INTO billing_workspace_links(workspace_id,account_id,attached_at) VALUES(?,?,?)',(workspace,account,stamp))
    if account!=workspace:
        check_limits(c,account)
        c.execute("INSERT INTO audit_log(id,organization_id,actor,action,entity,result,details_json,created_at) VALUES(?,?,?,'BILLING_ACCOUNT_SELECTED_AT_CREATION',?,'SUCCESS',?,?)",(str(uuid.uuid4()),workspace,actor,'billing-account:'+account,json.dumps({'selected_account':account}),stamp))

def summary(c,org,actor):
    if not membership_role(c,actor,org):raise HTTPException(403,'Active workspace membership required.')
    account=anchor(c,org);manage=admin(c,account,actor) if enabled(org) else membership_role(c,actor,org)=='OWNER';return {'id':account,'name':c.execute('SELECT name FROM organizations WHERE id=?',(account,)).fetchone()[0],'shared':account!=org,'can_manage':manage,'can_select_at_creation':manage and enabled(org) and not pilot()}

def operation(c,org,op):
    account=anchor(c,org)
    from app.billing.subscription_access import in_setup
    # Setup jobs keep their original workspace-owned reservation keys, even after
    # an attachment. The admission limit is summed across the account under its lock.
    if in_setup(org):return org,op
    # Setup entitlements have job-specific validation. Product usage keys include the
    # originating workspace so a caller cannot reuse another workspace's operation ID.
    if op.startswith('shared-ws:'):raise ValueError('Reserved operation namespace')
    return account,op if account==org else 'shared-ws:'+org+':'+op

def capacity_used(c,account,dimension,*,incoming=None,pending=False,all_monitors=False):
    if dimension=='monitors':
        status="m.status<>'Archived'" if all_monitors else "m.status='Active'"
        return c.execute('SELECT count(*) FROM intent_monitors m JOIN billing_workspace_links l ON l.workspace_id=m.organization_id WHERE l.account_id=? AND '+status,(account,)).fetchone()[0]
    q="SELECT lower(m.user_id) person FROM organization_memberships m JOIN billing_workspace_links l ON l.workspace_id=m.organization_id WHERE l.account_id=? AND m.status='ACTIVE'";args=[account]
    if pending:
        q+=" UNION SELECT lower(i.email) FROM workspace_invitations i JOIN billing_workspace_links l ON l.workspace_id=i.organization_id WHERE l.account_id=? AND i.status='PENDING' AND i.expires_at>?";args.extend([account,now()])
    return c.execute('SELECT count(DISTINCT person) FROM ('+q+') AS people'+(' WHERE person<>?' if incoming else ''),args+([incoming.lower()] if incoming else [])).fetchone()[0]

def attach_empty(c,account,org,actor,administrator,reason):
    """Offline operator transaction only; caller verifies DB ownership. Never reparent an established financial relationship."""
    if not enabled() or org==account or not administrator or not reason.strip():raise ValueError('Explicit distinct billing account, workspace and reason required')
    if pilot():
        from app.billing.owner_starter import OWNER
        if (account,org,actor)!=(PILOT_ACCOUNT,PILOT_CHILD,OWNER):raise HTTPException(403,'Outside the authorized owner pilot.')
    for key in sorted([account,org]):lock(c,key)
    if anchor(c,account)!=account or not admin(c,account,actor) or membership_role(c,actor,org)!='OWNER':raise HTTPException(403,'Authority over both account and workspace is required.')
    for key in (org,account):
        if not c.execute("SELECT 1 FROM organizations WHERE id=? AND created_by_user_id=? AND status='ACTIVE'",(key,actor)).fetchone() or c.execute("SELECT count(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE' AND role='OWNER'",(key,)).fetchone()[0]!=1:raise HTTPException(409,'Ownership requires review.')
    if not c.execute("SELECT 1 FROM customer_accounts WHERE user_id=? AND status='ACTIVE' AND verified_at IS NOT NULL",(actor,)).fetchone():raise HTTPException(403,'Verified account owner required.')
    current=anchor(c,org)
    if current==account:return False
    if current!=org or c.execute('SELECT count(*) FROM billing_workspace_links WHERE account_id=?',(org,)).fetchone()[0]!=1:raise HTTPException(409,'Workspace already has dependent billing relationships.')
    check_relationships(c,account)
    for table in ('subscription_customers','subscription_contracts','subscription_checkouts','subscription_payments','subscription_trials','subscription_billing_profiles','subscription_usage','subscription_reservations','commercial_contracts','access_periods','billing_customers','billing_payments','billing_subscriptions','payu_access_orders','launch_trial_claims'):
        if c.execute(f'SELECT 1 FROM {table} WHERE organization_id=? LIMIT 1',(org,)).fetchone():raise HTTPException(409,'Independent billing history requires manual reconciliation.')
    if c.execute("SELECT 1 FROM audit_log WHERE organization_id=? AND action='OWNER_STARTER_DEVELOPMENT_GRANTED'",(org,)).fetchone():raise HTTPException(409,'Independent complimentary grant requires reconciliation.')
    if not c.execute('UPDATE billing_workspace_links SET account_id=?,attached_at=? WHERE workspace_id=? AND account_id=?',(account,now(),org,org)).rowcount:raise HTTPException(409,'Billing association changed.')
    check_limits(c,account)
    from app.billing import owner_starter
    dev=owner_starter.active(c,account)
    details={'previous_account':org,'account':account,'verified_owner':actor,'reason':reason,'development_grant':dev['grant_id'] if dev else None,'unchanged_expiry':dev['paid_end'] if dev else None}
    c.execute('DELETE FROM billing_account_admins WHERE account_id=?',(org,));c.execute('DELETE FROM workspace_billing_accounts WHERE id=?',(org,));c.execute("INSERT INTO audit_log(id,organization_id,actor,action,entity,result,details_json,created_at) VALUES(?,?,?,'BILLING_ACCOUNT_ATTACHED',?,'SUCCESS',?,?)",(str(uuid.uuid4()),org,administrator,'billing-account:'+account,json.dumps(details),now()));return True

def check_relationships(c,account):
    if c.execute("SELECT count(*) FROM subscription_contracts WHERE organization_id=? AND environment=? AND status NOT IN ('expired','canceled')",(account,get_settings().creem_environment)).fetchone()[0]>1:raise HTTPException(409,'Multiple current provider contracts require reconciliation.')

def check_limits(c,account):
    from app.billing import contracts
    grant=contracts.active(c,account)
    if grant:
        limits=contracts.snapshot(grant)['limits']
        if capacity_used(c,account,'team_members',pending=True)>limits['team_members'] or capacity_used(c,account,'monitors',all_monitors=bool(grant.get('is_trial')))>limits['monitors']:raise HTTPException(409,'Attaching this workspace would exceed account capacity.')
