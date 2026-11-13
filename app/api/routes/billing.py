"""Signed workspace billing; raw webhooks have a separate exact-path verifier."""
from uuid import UUID
from fastapi import APIRouter,Depends,Request,Query,HTTPException
from app.api.dependencies import get_db
from app.billing import service,catalog,webhooks,provider

router=APIRouter(tags=['Workspace billing'])

def safe(operation,*args):
    try:return operation(*args)
    except (provider.ProviderRejected,provider.ProviderUnavailable):
        raise HTTPException(502,'Razorpay Test Mode could not verify this action. No payment or access is assumed; check provider status before retrying.') from None

@router.get('/organization/billing')
def info(c=Depends(get_db,scope='function')):return service.info(c)

@router.get('/organization/billing/plan-intent')
def intent(product:str=Query(max_length=40),plan:str=Query(max_length=30),c=Depends(get_db,scope='function')):
    service.access(c)
    return catalog.handoff(product,plan)

@router.post('/organization/billing/subscriptions',status_code=201)
def create(body:service.Create,c=Depends(get_db,scope='function')):return safe(service.create,c,body)

@router.get('/organization/billing/subscriptions/{key}/checkout')
def checkout(key:UUID,c=Depends(get_db,scope='function')):return safe(service.checkout,c,str(key))

@router.post('/organization/billing/subscriptions/{key}/verify')
def verify(key:UUID,body:service.Verification,c=Depends(get_db,scope='function')):return safe(service.verify,c,str(key),body)

@router.post('/organization/billing/subscriptions/{key}/reconcile')
def sync(key:UUID,c=Depends(get_db,scope='function')):return safe(service.sync,c,str(key))

@router.post('/organization/billing/subscriptions/{key}/recover')
def recover(key:UUID,c=Depends(get_db,scope='function')):return safe(service.recover,c,str(key))

@router.post('/organization/billing/subscriptions/{key}/cancel')
def cancel(key:UUID,body:service.Cancel,c=Depends(get_db,scope='function')):return safe(service.cancel,c,str(key),body)

@router.post('/billing/webhooks/razorpay',status_code=202)
async def webhook(request:Request):
    # Stream bounded bytes before parsing; verify EXACT original bytes.
    provider.guard();raw=bytearray()
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
