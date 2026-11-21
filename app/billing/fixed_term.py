"""Tenant-scoped history of retired fixed-term orders. No provider transport."""
import json,uuid
from pydantic import BaseModel,ConfigDict
from fastapi import HTTPException
from app.api.organization import membership_role
from app.database.prospects import now
from app.developer.keys import lock
from app.platform.context import current

class RefundRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:uuid.UUID


def manager(c,org=None):
    ctx=current();org=org or ctx.organization_id
    if org!=ctx.organization_id or membership_role(c,ctx.actor,org)!='OWNER':raise HTTPException(403,'Only the active workspace owner can manage payments.')
    return ctx

def public(row):
    result={key:row[key] for key in ('id','provider','mode','plan_code','interval','terms_version','currency','subtotal_minor','tax_minor','total_minor','status','period_start','period_end','verified_at','created_at')}
    result['automatic_renewal']=False
    result['tax']=json.loads(row['tax_json'])
    return result

def owned(c,key):
    ctx=manager(c)
    row=c.execute('SELECT * FROM payu_access_orders WHERE id=? AND organization_id=?',(key,ctx.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Payment order not found in this workspace.')
    return dict(row)

def history(c):
    ctx=manager(c)
    return {'items':[public(r) for r in c.execute('SELECT * FROM payu_access_orders WHERE organization_id=? ORDER BY created_at DESC,id DESC LIMIT 50',(ctx.organization_id,)).fetchall()],'refunds':[dict(r) for r in c.execute('SELECT order_id,amount_minor,currency,status,updated_at FROM payu_refund_observations WHERE organization_id=? ORDER BY updated_at DESC LIMIT 100',(ctx.organization_id,)).fetchall()],'refund_requests':[dict(r) for r in c.execute('SELECT id,order_id,status,created_at FROM payu_access_refunds WHERE organization_id=? ORDER BY created_at DESC LIMIT 50',(ctx.organization_id,)).fetchall()],'checkout_enabled':False,'blockers':['Fixed-term purchases are retired. Use Creem for new subscriptions.'],'yearly_prices_approved':False,'renewal':'Manual renewal only; no automatic charges.','upgrade_policy':'Plan changes take effect after existing paid access expires. No early upgrades, proration or unused-time credits.'}

def refund_request(c,key,body):
    row=owned(c,key);lock(c,row['organization_id'])
    if row['status']!='PAID' or not row['provider_payment_id']:raise HTTPException(409,'Only a verified payment can be reviewed for refund.')
    previous=c.execute('SELECT * FROM payu_access_refunds WHERE organization_id=? AND request_id=?',(row['organization_id'],str(body.request_id))).fetchone()
    if previous:
        if previous['order_id']!=key:raise HTTPException(409,'Refund request belongs to a different purchase.')
        return {'id':previous['id'],'status':previous['status'],'money_refunded':False}
    pending=c.execute("SELECT id,status FROM payu_access_refunds WHERE organization_id=? AND order_id=? AND status IN ('REQUESTED','REVIEW','PENDING') ORDER BY created_at LIMIT 1",(row['organization_id'],key)).fetchone()
    if pending:return {'id':pending['id'],'status':pending['status'],'money_refunded':False}
    key_refund=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO payu_access_refunds(id,organization_id,order_id,requested_by,request_id,amount_minor,currency,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'REQUESTED',?,?)",(key_refund,row['organization_id'],key,current().actor,str(body.request_id),row['total_minor'],row['currency'],stamp,stamp))
    return {'id':key_refund,'status':'REQUESTED','money_refunded':False,'message':'Your refund request is recorded for review under the applicable purchase policy. No refund is assumed pending independent review.'}
