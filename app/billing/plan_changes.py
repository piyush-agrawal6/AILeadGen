"""Change the renewal product of one verified paid contract; never create another subscription."""
import time,uuid
from typing import Literal
from pydantic import BaseModel,ConfigDict
from fastapi import HTTPException
from app.billing import subscriptions as sub,subscription_access as access,commercial,creem
from app.database.connection import db_session
from app.database.prospects import now
from app.developer.keys import lock

class Change(BaseModel):
 model_config=ConfigDict(extra='forbid')
 request_id:uuid.UUID
 expected_contract:uuid.UUID
 expected_period_end:int
 plan_code:Literal['starter','growth','scale']
 terms_version:str
 accepted_renewal:Literal[True]

def pending(c,contract,env):
 return c.execute("SELECT * FROM subscription_plan_changes WHERE contract_id=? AND environment=? AND status IN ('REQUESTED','CONFIRMED','REVIEW')",(contract,env)).fetchone()

def schema_ready(c):
 version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
 return version>=(1012 if version>=1000 else 54)

def change(body):
 from app.config.settings import get_settings
 from app.billing.subscription_sync import ref,reconcile_subscription
 s=get_settings();env=s.creem_environment
 with db_session() as c:
  ctx=sub.owner(c);org=ctx.organization_id;lock(c,org)
  if not schema_ready(c):raise HTTPException(503,'Plan changes require the billing schema upgrade.')
  if not access.enabled() or sub.blockers(c,org,'paid') or not s.subscription_terms_version or body.terms_version!=s.subscription_terms_version:raise HTTPException(409,'Review the current subscription terms and provider readiness.')
  current=access.active(c,org)
  if not current or current['provider_status']!='active' or current['is_trial'] or current['id']!=str(body.expected_contract) or current['period_end']!=body.expected_period_end:raise HTTPException(409,'The paid subscription or billing period changed. Refresh billing.')
  previous=c.execute('SELECT * FROM subscription_plan_changes WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
  if previous:
   if previous['actor']!=ctx.actor or previous['contract_id']!=current['id'] or previous['plan_code']!=body.plan_code:raise HTTPException(409,'This request already belongs to another change.')
   return {'status':previous['status'],'effective_at':previous['effective_at']}
  if current['plan_code']==body.plan_code or pending(c,current['id'],env):raise HTTPException(409,'This plan is current or another change requires confirmation.')
  mapping=c.execute("SELECT product_id FROM subscription_products WHERE environment=? AND provider='creem' AND plan_code=? AND variant='paid' AND catalog_hash=?",(env,body.plan_code,commercial.catalog()['catalog_sha256'])).fetchone()
  if not mapping:raise HTTPException(409,'Paid product mapping is unavailable.')
  product=mapping['product_id'];pid=creem.identifier(current['provider_id'],'sub_')
  try:
   remote=creem.object_mode(creem.get_subscription(pid,mode=env),env)
   from app.billing.subscription_sync import epoch
   if remote.get('id')!=pid or ref(remote.get('customer'))!=current['customer_id'] or remote.get('status')!='active' or epoch(remote.get('current_period_end_date'))!=body.expected_period_end or time.time()>=body.expected_period_end:raise creem.Rejected('Subscription changed')
   target=creem.validate_product(creem.get_product(product,mode=env),commercial.plan(body.plan_code),'paid',env)
   if target['id']!=product:raise creem.Rejected('Product mismatch')
  except (creem.Unavailable,creem.Rejected):raise HTTPException(502,'Creem could not confirm the subscription and requested product.') from None
  key=str(uuid.uuid4());c.execute("INSERT INTO subscription_plan_changes(id,organization_id,environment,contract_id,actor,request_id,product_id,plan_code,terms_version,effective_at,created_at,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'REQUESTED')",(key,org,env,current['id'],ctx.actor,str(body.request_id),product,body.plan_code,body.terms_version,body.expected_period_end,now()))
 try:
  creem.request('POST','/subscriptions/'+pid+'/upgrade',mode=env,body={'product_id':product,'update_behavior':'proration-none'})
  reconcile_subscription(pid,env)
 except (creem.Unavailable,creem.Rejected):
  with db_session() as c:c.execute("UPDATE subscription_plan_changes SET status='REVIEW' WHERE id=? AND status='REQUESTED'",(key,))
  raise HTTPException(502,'Plan change awaits provider confirmation. Refresh status before trying again.') from None
 with db_session() as c:
  row=c.execute('SELECT status,effective_at FROM subscription_plan_changes WHERE id=?',(key,)).fetchone();return dict(row)
