from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import current
from app.api.organization import products, membership_role
from app.api.permissions import authorize

def _deferred(c, organization_id):
    import json
    row=c.execute('SELECT preferences_json FROM organization_setup WHERE organization_id=?',(organization_id,)).fetchone()
    if not row or not row[0]:return False
    try:return bool(json.loads(row[0]).get('setup_deferred',False))
    except (ValueError,TypeError,AttributeError):return False

def _enabled(c, organization_id, row):
    settings=get_settings();stage=settings.intent_radar_stage
    from app.billing.subscription_access import required,product_grant
    has_sub_grant=bool(product_grant(c,organization_id))
    if required(c,organization_id) and not has_sub_grant:return False
    ready=bool(row and (row['onboarding_status']=='COMPLETED' or _deferred(c,organization_id)))
    enabled=bool(row and row['organization_status']=='ACTIVE' and ready and stage!='Disabled')
    if enabled and not row['manual_grant']:
        if has_sub_grant:
            enabled=True
        else:
            from app.billing.service import granted
            enabled='INTENT_RADAR' in granted(c,organization_id) if settings.billing_enabled else False
    if stage=='Internal Preview' and organization_id not in settings.intent_radar_internal_workspaces.split(','):enabled=False
    return enabled

def _access_state(c, organization_id, row, enabled):
    settings=get_settings()
    if not row or row['organization_status']!='ACTIVE':
        return {'access_state':'RESTRICTED','onboarding_status':None,'setup_deferred':False,'subscription_required':False,'subscription_active':False,'contract_status':None,'period_end':None,'trial_eligible':False}
    from app.billing.subscription_access import required,product_grant,enabled as sub_enabled
    from app.billing.subscriptions import trial_available
    onboarding_status=row['onboarding_status'] or 'IN_PROGRESS'
    deferred=_deferred(c,organization_id)
    sub_req=bool(required(c,organization_id))
    grant=product_grant(c,organization_id)
    sub_active=bool(grant)
    contract_row=None
    pending_checkout=None
    if sub_enabled():
        env=settings.creem_environment
        from app.billing.accounts import anchor
        account=anchor(c,organization_id)
        contract_row=c.execute(
            '''SELECT p.status,p.period_end,p.trial_start,p.period_start,p.cancel_confirmed_at
               FROM subscription_contracts p JOIN subscription_workspace_slots w
                 ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment
               WHERE p.organization_id=? AND p.environment=?''',
            (account,env),
        ).fetchone()
        pending_checkout=c.execute(
            "SELECT id,status FROM subscription_checkouts WHERE organization_id=? AND environment=? AND status IN ('CREATING','PENDING','REVIEW') ORDER BY created_at DESC LIMIT 1",
            (account,env),
        ).fetchone()
    trial_ok=False
    try:
        ctx=current()
        trial_ok=bool(sub_enabled() and not sub_active and trial_available(c,ctx.actor,organization_id))
    except Exception:
        trial_ok=False
    c_status=contract_row['status'] if contract_row else None
    period_end=contract_row['period_end'] if contract_row else None
    if enabled:
        if grant and grant.get('is_trial'):
            state='CANCELED_REMAINING' if c_status in ('canceled','scheduled_cancel') else 'TRIAL_ACTIVE'
        elif grant and grant.get('source_kind')!='COMPLIMENTARY' and c_status in ('canceled','scheduled_cancel'):
            state='CANCELED_REMAINING'
        else:
            state='ACTIVE'
    elif settings.intent_radar_stage=='Disabled':
        state='RESTRICTED'
    elif onboarding_status!='COMPLETED' and not deferred:
        state='SETUP_REQUIRED'
    elif pending_checkout:
        state='PAYMENT_PENDING'
    elif (sub_req or (not row['manual_grant'] and sub_enabled())) and not sub_active:
        if contract_row and c_status in ('expired','canceled','past_due','unpaid','refunded','disputed'):
            state='EXPIRED'
        elif trial_ok:
            state='TRIAL_AVAILABLE'
        else:
            state='SUBSCRIPTION_REQUIRED'
    else:
        state='RESTRICTED'
    return {
        'access_state':state,
        'onboarding_status':onboarding_status,
        'setup_deferred':deferred,
        'subscription_required':sub_req,
        'subscription_active':sub_active,
        'contract_status':c_status,
        'period_end':period_end,
        'trial_eligible':trial_ok,
    }

def availability(c, organization_id):
    # One scoped query; no permission cache survives a request or provider call.
    row=c.execute("""SELECT o.status organization_status,b.status onboarding_status,COALESCE(p.enabled,0) manual_grant
        FROM organizations o LEFT JOIN organization_onboarding b ON b.organization_id=o.id
        LEFT JOIN organization_products p ON p.organization_id=o.id AND p.product='INTENT_RADAR' WHERE o.id=?""",(organization_id,)).fetchone() if organization_id else None
    enabled=_enabled(c,organization_id,row)
    meta=_access_state(c,organization_id,row,enabled)
    settings=get_settings()
    actions_allowed=settings.app_env!='production' or organization_id in {x.strip() for x in settings.radar_action_workspaces.split(',')}
    return {'enabled':enabled,'actions_enabled':enabled and settings.radar_actions_enabled and actions_allowed,'stage':settings.intent_radar_stage,'product':'Intent Radar',**meta}

def context(c, write=False, manager=False):
    ctx=current()
    from app.billing.subscription_access import require_product
    require_product(c,ctx.organization_id)
    row=c.execute("""SELECT m.role,o.status organization_status,b.status onboarding_status,COALESCE(p.enabled,0) manual_grant
        FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id
        LEFT JOIN organization_onboarding b ON b.organization_id=o.id
        LEFT JOIN organization_products p ON p.organization_id=o.id AND p.product='INTENT_RADAR'
        WHERE m.organization_id=? AND m.user_id=? AND m.status='ACTIVE'""",(ctx.organization_id,ctx.actor)).fetchone()
    if not row or row['organization_status']!='ACTIVE':raise HTTPException(403,'Active workspace membership is required.')
    if not _enabled(c,ctx.organization_id,row):raise HTTPException(404,'Intent Radar is not enabled for this workspace.')
    if write:
        from app.billing.access_periods import require_current
        require_current(c,ctx.organization_id)
        authorize(c,ctx.actor,'POST','/api/intent-radar',{},ctx.organization_id)
    if manager and row['role'] not in ('OWNER','ADMIN'):raise HTTPException(403,'Intent Radar settings require a workspace administrator.')
    return ctx

def persistence_context(c,manager=False):
    """Lock authorization rows before resource rows, closing revoke/check/write races."""
    ctx=context(c,True,manager)
    role="role IN ('OWNER','ADMIN')" if manager else "role<>'VIEWER'"
    if not c.execute("UPDATE organization_memberships SET role=role WHERE organization_id=? AND user_id=? AND status='ACTIVE' AND "+role,(ctx.organization_id,ctx.actor)).rowcount:
        raise HTTPException(403,'Workspace write permission was revoked before persistence.')
    if not c.execute("UPDATE organization_products SET enabled=enabled WHERE organization_id=? AND product='INTENT_RADAR' AND enabled=1",(ctx.organization_id,)).rowcount:
        from app.billing.subscription_access import product_grant
        from app.billing.service import fence_grant
        if not product_grant(c,ctx.organization_id) and not fence_grant(c,ctx.organization_id):raise HTTPException(404,'Intent Radar access was revoked before persistence.')
    if not c.execute("UPDATE organization_onboarding SET status=status WHERE organization_id=? AND status='COMPLETED'",(ctx.organization_id,)).rowcount and not _deferred(c,ctx.organization_id):
        raise HTTPException(404,'Workspace access changed before persistence.')
    return ctx
