"""Provider callbacks bypass only the application broker, never signature checks."""
import asyncio
from fastapi import APIRouter,Request,HTTPException,Depends
from app.api.dependencies import get_db
from app.billing import creem_events
router=APIRouter(prefix='/billing',tags=['Subscriptions'])

from app.billing import subscriptions as service
from app.billing import plan_changes

@router.post('/subscription/change')
def change(body:plan_changes.Change):return plan_changes.change(body)

@router.get('/subscription')
def status(c=Depends(get_db,scope='function')):return service.summary(c)

@router.post('/subscription/checkout',status_code=202)
def checkout(body:service.Checkout):return service.start(body)

@router.post('/subscription/cancel')
def cancel(body:service.Action):return service.cancel(body)

@router.post('/subscription/portal')
def portal():return service.portal()

@router.post('/subscription/refresh')
def refresh(c=Depends(get_db,scope='function')):
 ctx=service.owner(c)
 from app.config.settings import get_settings
 from app.accounts.security import limited
 if limited(c,'subscription-refresh',ctx.organization_id,6,60):raise HTTPException(429,'Wait before refreshing the provider again.')
 from app.billing.creem import Unavailable,Rejected
 try:service.refresh_checkout(c,ctx.organization_id)
 except (Unavailable,Rejected):raise HTTPException(502,'The checkout status could not be confirmed. Your setup remains saved; no access was granted.') from None
 row=c.execute('SELECT p.provider_id,p.environment FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.contract_id=p.id AND w.organization_id=p.organization_id AND w.environment=p.environment WHERE p.organization_id=? AND p.environment=?',(ctx.organization_id,get_settings().creem_environment)).fetchone()
 if not row:return service.summary(c)
 c.commit()
 from app.billing.subscription_sync import reconcile_subscription
 from app.billing.creem import Unavailable,Rejected
 try:reconcile_subscription(row['provider_id'],row['environment'])
 except (Unavailable,Rejected):raise HTTPException(502,'The provider status could not be confirmed. No access change is assumed.') from None
 return service.summary(c)

@router.post('/webhooks/creem')
async def webhook(request:Request):
 raw=bytearray()
 async for chunk in request.stream():
  raw.extend(chunk)
  if len(raw)>creem_events.MAX_BYTES:raise HTTPException(413,'Webhook payload exceeds the allowed size.')
 result=await asyncio.to_thread(creem_events.receive,bytes(raw),request.headers.get('creem-signature',''))
 from app.config.settings import get_settings
 try:await asyncio.to_thread(creem_events.dispatch_event,result['event_id'],get_settings().creem_environment)
 except Exception:raise HTTPException(503,'Webhook stored; worker dispatch is unavailable. Retry this event.') from None
 return result

@router.post('/webhooks/creem/test')
async def test_webhook(request:Request):
 raw=bytearray()
 async for chunk in request.stream():
  raw.extend(chunk)
  if len(raw)>creem_events.MAX_BYTES:raise HTTPException(413,'Webhook payload exceeds the allowed size.')
 result=await asyncio.to_thread(creem_events.receive,bytes(raw),request.headers.get('creem-signature',''),environment='test')
 try:await asyncio.to_thread(creem_events.dispatch_event,result['event_id'],'test')
 except Exception:raise HTTPException(503,'Webhook stored; worker dispatch is unavailable. Retry this event.') from None
 return result
