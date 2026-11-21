"""Workspace-scoped access and read-only history of the retired sandbox."""
import json
from fastapi import HTTPException
from app.config.settings import get_settings
from app.platform.context import current
from app.api.organization import require_role
from app.developer.keys import lock

def enabled():
    if not get_settings().billing_enabled:raise HTTPException(404,'Workspace billing is not enabled.')

def access(c,manager=False):
    enabled();ctx=current()
    require_role(c,ctx.actor,ctx.organization_id,('OWNER',) if manager else ('OWNER','ADMIN'))
    return ctx

def granted(c,org):
    from app.billing.contracts import active
    return {'INTENT_RADAR'} if active(c,org) else set()

def fence_grant(c,org):
    lock(c,org)
    return bool(granted(c,org))

def info(c):
    ctx=access(c);org=ctx.organization_id
    rows=c.execute('SELECT id,plan_code,plan_json,mode,status,current_start,current_end,paid_start,paid_end,cancel_at_cycle_end,last_reconciled_at,created_at,updated_at FROM billing_subscriptions WHERE organization_id=? ORDER BY created_at DESC,id DESC LIMIT 20',(org,)).fetchall()
    payments=c.execute('SELECT provider_id,subscription_id,mode,amount,currency,status,period_start,period_end,recorded_at FROM billing_payments WHERE organization_id=? ORDER BY recorded_at DESC,provider_id DESC LIMIT 50',(org,)).fetchall()
    subscriptions=[]
    for row in rows:
        item=dict(row);item.update(plan=json.loads(item.pop('plan_json')),commercial_entitlement=False,test_only=True,settled_current_period=False);subscriptions.append(item)
    return {'mode':'test','provider':'razorpay','provider_configured':False,'webhook_configured':False,'controlled_workspace':False,'can_manage':False,'checkout_available':False,'public_checkout_enabled':False,'commercial_pricing_approved':False,'provider_health':'Retired; historical records only','plans':[],'subscriptions':subscriptions,'payments':[dict(p) for p in payments],'usage':[],'manual_access_preserved':True,'plan_changes':'Current subscriptions are managed through Creem.'}
