from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import current
from app.api.organization import products, membership_role
from app.api.permissions import authorize

def _enabled(c, organization_id, row):
    settings=get_settings();stage=settings.intent_radar_stage
    from app.billing.subscription_access import required,product_grant
    if required(c,organization_id) and not product_grant(c,organization_id):return False
    enabled=bool(row and row['organization_status']=='ACTIVE' and row['onboarding_status']=='COMPLETED' and stage!='Disabled')
    if enabled and not row['manual_grant']:
        from app.billing.service import granted
        enabled='INTENT_RADAR' in granted(c,organization_id) if settings.billing_enabled or settings.payu_billing_enabled else False
    if stage=='Internal Preview' and organization_id not in settings.intent_radar_internal_workspaces.split(','):enabled=False
    return enabled

def availability(c, organization_id):
    # One scoped query; no permission cache survives a request or provider call.
    row=c.execute("""SELECT o.status organization_status,b.status onboarding_status,COALESCE(p.enabled,0) manual_grant
        FROM organizations o LEFT JOIN organization_onboarding b ON b.organization_id=o.id
        LEFT JOIN organization_products p ON p.organization_id=o.id AND p.product='INTENT_RADAR' WHERE o.id=?""",(organization_id,)).fetchone() if organization_id else None
    return {'enabled':_enabled(c,organization_id,row),'stage':get_settings().intent_radar_stage,'product':'Intent Radar'}

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
        from app.billing.service import fence_grant
        if not fence_grant(c,ctx.organization_id):raise HTTPException(404,'Intent Radar access was revoked before persistence.')
    if not c.execute("UPDATE organization_onboarding SET status=status WHERE organization_id=? AND status='COMPLETED'",(ctx.organization_id,)).rowcount:
        raise HTTPException(404,'Workspace access changed before persistence.')
    return ctx
