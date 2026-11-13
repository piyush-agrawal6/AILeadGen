from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import current
from app.api.organization import products, membership_role
from app.api.permissions import authorize

def availability(c, organization_id):
    settings = get_settings()
    stage = settings.intent_radar_stage
    enabled = bool(organization_id and stage != 'Disabled' and products(c, organization_id).get('INTENT_RADAR'))
    if enabled:
        row=c.execute("SELECT status FROM organization_onboarding WHERE organization_id=?",(organization_id,)).fetchone()
        enabled=bool(row and row[0]=='COMPLETED')
    if stage == 'Internal Preview' and organization_id not in settings.intent_radar_internal_workspaces.split(','): enabled = False
    return {'enabled': enabled, 'stage': stage, 'product': 'Intent Radar'}

def context(c, write=False, manager=False):
    ctx = current()
    if not membership_role(c, ctx.actor, ctx.organization_id): raise HTTPException(403, 'Active workspace membership is required.')
    if not availability(c, ctx.organization_id)['enabled']: raise HTTPException(404, 'Intent Radar is not enabled for this workspace.')
    if write: authorize(c, ctx.actor, 'POST', '/api/intent-radar', {}, ctx.organization_id)
    if manager and membership_role(c, ctx.actor, ctx.organization_id) not in ('OWNER', 'ADMIN'): raise HTTPException(403, 'Intent Radar settings require a workspace administrator.')
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
