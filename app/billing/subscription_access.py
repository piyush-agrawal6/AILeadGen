"""Payment-gated product access and an isolated, bounded setup-only AI budget.

Neither a setup allowance nor a browser return can create a trial entitlement.
Historical trial/payment snapshots are intentionally left intact.
"""
import json,time,hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import current

POLICY='planebyte-card-trial-2026-11-17-v2'
TRIAL_SECONDS=259200
TRIAL_LIMITS={'searches':5,'ai_calls':3,'ai_tokens':150000,'monitors':1,'monitor_executions':0,'reports':0,'team_members':1,'api_requests':0,'monitor_interval_hours':24}
_setup=ContextVar('verified_subscription_setup_job',default=None)

def enabled():return get_settings().subscription_onboarding_required
def required(c,org):
 return bool(enabled() and c.execute('SELECT 1 FROM subscription_requirements WHERE organization_id=?',(org,)).fetchone())
def enroll(c,actor,org):
 if not enabled():return False
 c.execute('INSERT INTO subscription_requirements(organization_id,registered_by,policy_version,created_at) VALUES(?,?,?,?) ON CONFLICT(organization_id) DO NOTHING',(org,actor,POLICY,now()))
 return True

def has_contract(c,org):
 return bool(enabled() and c.execute('SELECT 1 FROM subscription_workspace_slots WHERE organization_id=? AND environment=?',(org,get_settings().creem_environment)).fetchone())

def active(c,org):
 if not enabled():return None
 s=get_settings();environment=s.creem_environment;stamp=int(time.time())
 if environment=='test' and org not in {x.strip() for x in s.billing_test_workspaces.split(',') if x.strip()}:return None
 row=c.execute('''SELECT p.* FROM subscription_contracts p JOIN subscription_workspace_slots w
  ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment
  WHERE p.organization_id=? AND p.environment=?''',(org,environment)).fetchone()
 if not row or not row['verified_at'] or not row['period_start'] or not row['period_end'] or not row['period_start']<=stamp<row['period_end']:return None
 if row['status'] not in ('active','trialing','scheduled_cancel','canceled'):return None
 saved=json.loads(row['plan_json']);trial=row['trial_start'] is not None and row['period_start']==row['trial_start']
 if row['status']=='canceled' and not row['cancel_confirmed_at']:return None
 if not row['recurring_authorized'] and not row['cancel_confirmed_at']:return None
 if trial:
  claim=c.execute('SELECT * FROM subscription_trials WHERE organization_id=? AND contract_id=?',(org,row['id'])).fetchone()
  if not claim or claim['policy_version']!=POLICY or claim['ends_at']-claim['starts_at']!=TRIAL_SECONDS or claim['starts_at']!=row['period_start'] or claim['ends_at']!=row['period_end']:return None
  saved={**saved,'name':'3-day card trial → '+saved['name'],'limits':TRIAL_LIMITS,'trial_policy':POLICY}
 elif not c.execute("SELECT 1 FROM subscription_payments WHERE organization_id=? AND contract_id=? AND status='paid' AND period_start=? AND period_end=?",(org,row['id'],row['period_start'],row['period_end'])).fetchone():return None
 result=dict(row)
 result.update(plan_json=json.dumps(saved,sort_keys=True),paid_start=row['period_start'],paid_end=row['period_end'],mode='live' if environment=='production' else 'test',source_kind='SUBSCRIPTION',status='ACTIVE',catalog_version=saved.get('version',''))
 return result

def product_grant(c,org):
 value=active(c,org)
 if value:return value
 # A genuinely verified existing PayU one-time purchase is an allowed paid path.
 from app.billing.access_periods import active as legacy
 value=legacy(c,org)
 return value if value and value['source_kind']=='PAYMENT' else None

def require_product(c,org):
 if not required(c,org):return None
 value=product_grant(c,org)
 if not value:raise HTTPException(402,{'code':'PAYMENT_REQUIRED','message':'Complete Step 5: Choose Your Plan & Payment. A provider-confirmed card trial or verified paid purchase is required. Your saved onboarding and billing controls remain available.'})
 return value

def scheduled_sql(org):
 if org not in ('m.organization_id','j.organization_id'):raise ValueError('Internal scheduler alias required')
 s=get_settings();mode=s.creem_environment;stamp=int(time.time());approved=[v.strip() for v in s.billing_test_workspaces.split(',') if v.strip()][:100]
 restriction=''
 if mode=='test':restriction=' AND p.organization_id IN ('+','.join('?' for _ in approved)+')' if approved else ' AND 0=1'
 sql="EXISTS(SELECT 1 FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment JOIN subscription_payments t ON t.organization_id=p.organization_id AND t.contract_id=p.id AND t.period_start=p.period_start AND t.period_end=p.period_end WHERE p.organization_id="+org+" AND p.environment=? AND p.status IN ('active','scheduled_cancel','canceled') AND p.verified_at IS NOT NULL AND (p.recurring_authorized=1 OR p.cancel_confirmed_at IS NOT NULL) AND p.period_start<=? AND p.period_end>? AND t.status='paid'"+restriction+')'
 return sql,[mode,stamp,stamp,*(approved if mode=='test' else [])]

@contextmanager
def setup_scope(c,key):
 """Only an owned persisted setup job can use the prepayment AI ledger."""
 ctx=current();value=None
 if required(c,ctx.organization_id) and not product_grant(c,ctx.organization_id):
  row=c.execute('SELECT id,organization_id,created_by,source_kind FROM organization_profile_jobs WHERE id=? AND organization_id=?',(key,ctx.organization_id)).fetchone()
  if not row or row['created_by']!=ctx.actor or row['source_kind'] not in ('WEBSITE','DESCRIPTION','ICP_RECOMMENDATIONS','ONBOARDING_ADVICE'):raise HTTPException(403,'A verified setup job is required.')
  value={'organization_id':ctx.organization_id,'job_id':key,'kind':row['source_kind']}
 token=_setup.set(value)
 try:yield
 finally:_setup.reset(token)

def in_setup(org):
 value=_setup.get();return bool(value and value['organization_id']==org)

def setup_contract(c,org,amounts,operation_id):
 if not in_setup(org):return None
 if set(amounts)-{'ai_calls','ai_tokens'}:raise HTTPException(403,'Setup capacity cannot be used for product operations.')
 value=_setup.get();prefix={'WEBSITE':'company-profile:','DESCRIPTION':'company-profile:','ICP_RECOMMENDATIONS':'setup-icp:','ONBOARDING_ADVICE':'setup-advice:'}[value['kind']]
 parent=prefix+value['job_id']
 if operation_id!=parent and not operation_id.startswith('ai-attempt:'+hashlib.sha256(parent.encode()).hexdigest()[:32]+':'):raise HTTPException(403,'Setup capacity is bound to the owned setup job.')
 if not required(c,org):raise HTTPException(403,'Setup enrollment changed.')
 limits={**TRIAL_LIMITS,'searches':0,'monitors':0}
 return {'id':'setup:'+org,'paid_start':0,'paid_end':2147483647,'plan_json':json.dumps({'code':'setup-only','name':'Setup AI budget, not product or trial access','limits':limits})}
