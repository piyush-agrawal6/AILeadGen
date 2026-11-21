"""Signed workspace billing; raw webhooks have a separate exact-path verifier."""
from uuid import UUID
from fastapi import APIRouter,Depends,Request,Query,HTTPException
from app.api.dependencies import get_db
from app.billing import service,catalog,webhooks

router=APIRouter(tags=['Workspace billing'])

@router.get('/organization/billing')
def info(c=Depends(get_db,scope='function')):return service.info(c)

@router.get('/organization/billing/plan-intent')
def intent(product:str=Query(max_length=40),plan:str=Query(max_length=30),c=Depends(get_db,scope='function')):
    service.access(c)
    return catalog.handoff(product,plan)

# Exact compatibility endpoints cannot contact a gateway or issue entitlements.
@router.post('/organization/billing/subscriptions')
@router.get('/organization/billing/subscriptions/{key}/checkout')
@router.post('/organization/billing/subscriptions/{key}/verify')
@router.post('/organization/billing/subscriptions/{key}/reconcile')
@router.post('/organization/billing/subscriptions/{key}/recover')
@router.post('/organization/billing/subscriptions/{key}/cancel')
def retired():raise HTTPException(410,'Legacy checkout is retired. Use Billing & Subscription.')

@router.post('/billing/webhooks/razorpay',status_code=202)
async def webhook(request:Request):
    # Stream bounded bytes before parsing; verify EXACT original bytes.
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>262144:raise HTTPException(413,'Webhook body is too large.')
    body=bytes(raw);signature=request.headers.get('x-razorpay-signature','');event_id=request.headers.get('x-razorpay-event-id','')
    webhooks.validate(body,signature,event_id)
    def persist():
        from app.database.connection import db_session
        with db_session() as c:return webhooks.receive(c,body,signature,event_id)
    import asyncio
    return await asyncio.to_thread(persist)
