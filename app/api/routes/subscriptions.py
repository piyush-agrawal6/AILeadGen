"""Provider callbacks bypass only the application broker, never signature checks."""
import asyncio
from fastapi import APIRouter,Request,HTTPException
from app.billing import creem_events
router=APIRouter(prefix='/billing',tags=['Subscriptions'])

@router.post('/webhooks/creem')
async def webhook(request:Request):
 raw=bytearray()
 async for chunk in request.stream():
  raw.extend(chunk)
  if len(raw)>creem_events.MAX_BYTES:raise HTTPException(413,'Webhook payload exceeds the allowed size.')
 return await asyncio.to_thread(creem_events.receive,bytes(raw),request.headers.get('creem-signature',''))

@router.post('/webhooks/creem/test')
async def test_webhook(request:Request):
 raw=bytearray()
 async for chunk in request.stream():
  raw.extend(chunk)
  if len(raw)>creem_events.MAX_BYTES:raise HTTPException(413,'Webhook payload exceeds the allowed size.')
 return await asyncio.to_thread(creem_events.receive,bytes(raw),request.headers.get('creem-signature',''),environment='test')
