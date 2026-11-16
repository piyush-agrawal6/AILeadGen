"""Workspace-scoped fixed-term payment endpoints and one exact PayU callback."""
import asyncio,json
from urllib.parse import parse_qsl
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response
from app.api.dependencies import get_db
from app.billing import fixed_term as payment
router=APIRouter(tags=['Fixed-term workspace access'])
@router.get('/organization/billing/access')
def history(c=Depends(get_db,scope='function')):return payment.history(c)
@router.get('/organization/billing/access/quote')
def quote(plan:str,interval:str='monthly',c=Depends(get_db,scope='function')):
    payment.manager(c);return payment.quote(plan,interval)
@router.post('/organization/billing/access/orders',status_code=201)
def create(body:payment.Purchase):return payment.create(body)
@router.post('/organization/billing/access/orders/{key}/reconcile')
def reconcile(key:UUID):return payment.reconcile(str(key))
@router.get('/organization/billing/access/orders/{key}/receipt')
def receipt(key:UUID,c=Depends(get_db,scope='function')):
    row=payment.owned(c,str(key))
    if row['status'] not in ('PAID','REFUNDED') or not row['verified_at']:raise HTTPException(409,'A receipt is available after verified payment.')
    result={'document':'Payment receipt — not a GST tax invoice','purchase':payment.public(row),'payment_reference':row['provider_payment_id'],'automatic_renewal':False}
    return Response(json.dumps(result,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="planebyte-receipt-'+str(key)+'.json"','Cache-Control':'private, no-store'})
@router.post('/organization/billing/access/orders/{key}/refund-request',status_code=202)
def refund(key:UUID,body:payment.RefundRequest,c=Depends(get_db,scope='function')):return payment.refund_request(c,str(key),body)
@router.post('/billing/payments/payu/callback')
async def callback(request:Request):
    if request.headers.get('content-type','').split(';')[0].strip()!='application/x-www-form-urlencoded':raise HTTPException(415,'Unsupported payment callback format.')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>16384:raise HTTPException(413,'Payment callback exceeds its bound.')
    try:
        pairs=parse_qsl(raw.decode('utf-8'),keep_blank_values=True,max_num_fields=60,strict_parsing=True)
        fields=dict(pairs)
        if len(fields)!=len(pairs) or any(len(k)>100 or len(v)>2048 for k,v in pairs):raise ValueError()
    except (ValueError,UnicodeError):raise HTTPException(400,'Invalid payment callback.') from None
    try:return await asyncio.to_thread(payment.callback,fields)
    except payment.payu.PayURejected:raise HTTPException(400,'Invalid payment callback.') from None
