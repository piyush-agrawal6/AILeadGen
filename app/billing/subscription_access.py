"""Payment-gated product access and an isolated, bounded setup-only AI budget.

Neither a setup allowance nor a browser return can create a trial entitlement.
Historical trial/payment snapshots are intentionally left intact.
"""
import json,time,hashlib,uuid
from contextlib import contextmanager
from contextvars import ContextVar
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import current

POLICY='planebyte-card-trial-2026-11-17-v2'
TRIAL_SECONDS=259200
MAX_INTERNAL_TESTING_WINDOW_SECONDS=7*86400
TRIAL_LIMITS={'searches':5,'ai_calls':3,'ai_tokens':150000,'monitors':1,'monitor_executions':0,'reports':0,'team_members':1,'api_requests':0,'monitor_interval_hours':24}
# Dedicated bounded allowance for guided 5-step company/ICP/Copilot onboarding
# so setup never exhausts a workspace's product trial AI quota.
SETUP_LIMITS={'searches':0,'ai_calls':25,'ai_tokens':500000,'monitors':0,'monitor_executions':0,'reports':0,'team_members':1,'api_requests':0,'monitor_interval_hours':24}
_setup=ContextVar('verified_subscription_setup_job',default=None)

def is_trial_contract(row)->bool:
 return bool(row and row['trial_start'] is not None and row['period_start']==row['trial_start'])

def entitlement_label(row)->str|None:
 if not row:return None
 code=(row['plan_code'] or '').strip().lower()
 tier={'starter':'Starter','growth':'Growth','scale':'Scale','enterprise':'Enterprise'}.get(code,code.capitalize() or 'Subscription')
 return f'{tier} Trial' if is_trial_contract(row) else f'Paid {tier}'

def internal_testing_grant(c,org,base_contract,*,stamp=None):
 """Return a bounded, auto-expiring internal testing allowance ONLY when all checks pass.

 Security invariants:
 1. Requires explicit server-only workspace ID, owner email, and future UTC expiry.
 2. Expiry window cannot exceed MAX_INTERNAL_TESTING_WINDOW_SECONDS (7 days) and never
    extends past the verified contract's period_end.
 3. Requires an already active verified Creem contract (never bypasses payment verification).
 4. Requires an ACTIVE OWNER membership for the configured owner email on that exact workspace.
 5. Uses an isolated usage period key (usage_period_start = effective_expires_at > paid_start)
    so real trial/paid usage history in subscription_usage stays 100% preserved.
 """
 s=get_settings()
 now_ts=int(time.time()) if stamp is None else int(stamp)
 target_org=(s.internal_testing_workspace_id or '').strip()
 target_owner=(s.internal_testing_owner_email or '').strip().lower()
 configured_expires=int(s.internal_testing_expires_at or 0)
 if not target_org or not target_owner or configured_expires<=now_ts:return None
 if configured_expires-now_ts>MAX_INTERNAL_TESTING_WINDOW_SECONDS:return None
 if not base_contract or org!=target_org:return None
 effective_expires=min(configured_expires,int(base_contract['paid_end']))
 if effective_expires<=now_ts or effective_expires<=int(base_contract['paid_start']):return None
 owner_row=c.execute("SELECT 1 FROM organization_memberships WHERE organization_id=? AND LOWER(user_id)=? AND role='OWNER' AND status='ACTIVE'",(org,target_owner)).fetchone()
 if not owner_row:return None
 limits={
  'searches':int(s.internal_testing_searches_limit),
  'ai_calls':int(s.internal_testing_ai_calls_limit),
  'ai_tokens':int(s.internal_testing_ai_tokens_limit),
  'monitors':int(s.internal_testing_monitors_limit),
  'monitor_executions':int(s.internal_testing_monitor_executions_limit),
  'reports':int(s.internal_testing_reports_limit),
  'team_members':1,
  'api_requests':int(s.internal_testing_api_requests_limit),
  'monitor_interval_hours':24,
 }
 return {
  'active':True,
  'expires_at':effective_expires,
  'usage_period_start':effective_expires,
  'usage_period_end':effective_expires,
  'limits':limits,
 }

def record_internal_testing_audit(c,org,grant,*,contract_id,operation_id=None,dimensions=None):
 try:
  ctx=current();actor=ctx.actor
 except Exception:
  actor='system:internal-testing'
 details={'contract_id':contract_id,'expires_at':grant['expires_at'],'operation_id':operation_id,'dimensions':list(dimensions or []),'limits':grant['limits']}
 c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),actor,'INTERNAL_TESTING_ALLOWANCE_USED','internal-testing:'+org,'SUCCESS',json.dumps(details,sort_keys=True),org,now()))

def enabled():return get_settings().subscription_onboarding_required
def required(c,org):
 if not enabled():return False
 from app.billing.accounts import anchor
 account=anchor(c,org)
 return account!=org or bool(c.execute('SELECT 1 FROM subscription_requirements WHERE organization_id=?',(org,)).fetchone())
def enroll(c,actor,org):
 if not enabled():return False
 c.execute('INSERT INTO subscription_requirements(organization_id,registered_by,policy_version,created_at) VALUES(?,?,?,?) ON CONFLICT(organization_id) DO NOTHING',(org,actor,POLICY,now()))
 return True

def has_contract(c,org):
 from app.billing.accounts import anchor
 return bool(enabled() and c.execute('SELECT 1 FROM subscription_workspace_slots WHERE organization_id=? AND environment=?',(anchor(c,org),get_settings().creem_environment)).fetchone())

def active(c,org):
 if not enabled():return None
 from app.billing.accounts import anchor
 requested_org=org;org=anchor(c,org)
 s=get_settings();environment=s.creem_environment;stamp=int(time.time())
 if environment=='test' and not {org,requested_org}<={x.strip() for x in s.billing_test_workspaces.split(',') if x.strip()}:return None
 row=c.execute('''SELECT p.* FROM subscription_contracts p JOIN subscription_workspace_slots w
  ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment
  WHERE p.organization_id=? AND p.environment=?''',(org,environment)).fetchone()
 if not row or not row['verified_at'] or not row['period_start'] or not row['period_end'] or not row['period_start']<=stamp<row['period_end']:return None
 if row['status'] not in ('active','trialing','scheduled_cancel','canceled'):return None
 saved=json.loads(row['plan_json']);trial=is_trial_contract(row);label=entitlement_label(row)
 if row['status']=='canceled' and not row['cancel_confirmed_at']:return None
 if not row['recurring_authorized'] and not row['cancel_confirmed_at']:return None
 if trial:
  claim=c.execute('SELECT * FROM subscription_trials WHERE organization_id=? AND contract_id=?',(org,row['id'])).fetchone()
  if not claim or claim['policy_version']!=POLICY or claim['ends_at']-claim['starts_at']!=TRIAL_SECONDS or claim['starts_at']!=row['period_start'] or claim['ends_at']!=row['period_end']:return None
  saved={**saved,'name':label,'limits':TRIAL_LIMITS,'trial_policy':POLICY}
 elif not c.execute("SELECT 1 FROM subscription_payments WHERE organization_id=? AND contract_id=? AND status='paid' AND period_start=? AND period_end=?",(org,row['id'],row['period_start'],row['period_end'])).fetchone():return None
 else:
  saved={**saved,'name':label}
 base_limits=dict(saved['limits'])
 result=dict(row)
 result.update(plan_json=json.dumps(saved,sort_keys=True),paid_start=row['period_start'],paid_end=row['period_end'],usage_period_start=row['period_start'],usage_period_end=row['period_end'],mode='live' if environment=='production' else 'test',source_kind='SUBSCRIPTION',status='ACTIVE',provider_status=row['status'],is_trial=trial,entitlement_label=label,base_limits=base_limits,internal_testing=None,catalog_version=saved.get('version',''))
 grant=internal_testing_grant(c,org,result,stamp=stamp) if requested_org==org else None
 if grant:
  saved={**saved,'limits':grant['limits']}
  result.update(plan_json=json.dumps(saved,sort_keys=True),usage_period_start=grant['usage_period_start'],usage_period_end=grant['usage_period_end'],internal_testing={'active':True,'expires_at':grant['expires_at'],'limits':grant['limits']})
 return result

def product_grant(c,org,*,include_development=True):
 value=active(c,org)
 if value:return value
 # A genuinely verified existing PayU one-time purchase is an allowed paid path.
 from app.billing.access_periods import active as legacy
 value=legacy(c,org)
 if value and value['source_kind']=='PAYMENT':return value
 if include_development and enabled():
  from app.billing.owner_starter import active as development
  from app.billing.accounts import anchor
  return development(c,anchor(c,org))
 return None

def require_product(c,org):
 if not required(c,org):return None
 value=product_grant(c,org)
 if not value:raise HTTPException(402,{'code':'PAYMENT_REQUIRED','message':'This action needs an active subscription. Open Settings → Billing & Usage to check payment status or choose a plan. Your workspace data is saved.'})
 return value

def scheduled_sql(org):
 if org not in ('m.organization_id','j.organization_id'):raise ValueError('Internal scheduler alias required')
 from app.billing.accounts import enabled as shared,pilot,PILOT_ACCOUNT,PILOT_CHILD
 origin=org
 if shared():
  mapped='(SELECT billlink.account_id FROM billing_workspace_links billlink WHERE billlink.workspace_id='+org+')'
  org=(f"(CASE WHEN {org}='{PILOT_CHILD}' AND {mapped}='{PILOT_ACCOUNT}' THEN {mapped} ELSE {org} END)" if pilot() else mapped)
 s=get_settings();mode=s.creem_environment;stamp=int(time.time());approved=[v.strip() for v in s.billing_test_workspaces.split(',') if v.strip()][:100]
 restriction=''
 if mode=='test':restriction=' AND p.organization_id IN ('+','.join('?' for _ in approved)+')' if approved else ' AND 0=1'
 sql="EXISTS(SELECT 1 FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment JOIN subscription_payments t ON t.organization_id=p.organization_id AND t.contract_id=p.id AND t.period_start=p.period_start AND t.period_end=p.period_end WHERE p.organization_id="+org+" AND p.environment=? AND p.status IN ('active','scheduled_cancel','canceled') AND p.verified_at IS NOT NULL AND (p.recurring_authorized=1 OR p.cancel_confirmed_at IS NOT NULL) AND p.period_start<=? AND p.period_end>? AND t.status='paid'"+restriction+')'
 args=[mode,stamp,stamp,*(approved if mode=='test' else [])]
 if mode=='test' and approved and origin!=org:
  sql='('+sql+' AND '+origin+' IN ('+','.join('?' for _ in approved)+'))';args.extend(approved)
 from app.billing.owner_starter import configured_id,active as development,ISSUED,REVOKED,OWNER
 key=configured_id()
 if key:
  from app.database.connection import db_session
  with db_session() as c:
   receipt=c.execute('SELECT organization_id FROM audit_log WHERE id=? AND action=?',(key,ISSUED)).fetchone()
   grant=development(c,receipt[0]) if receipt else None
  if grant:
   sql='('+sql+' OR ('+org+'=? AND EXISTS(SELECT 1 FROM organization_memberships mbr WHERE mbr.organization_id='+org+" AND mbr.user_id=? AND mbr.role='OWNER' AND mbr.status='ACTIVE') AND NOT EXISTS(SELECT 1 FROM audit_log revoked WHERE revoked.id=? AND revoked.action=?)))"
   args.extend([grant['organization_id'],OWNER,key+':revoked',REVOKED])
 return sql,args

@contextmanager
def setup_scope(c,key):
 """Only an owned persisted setup job can use the isolated onboarding AI ledger."""
 ctx=current();value=None
 if required(c,ctx.organization_id):
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
 return {'id':'setup:'+org,'paid_start':0,'paid_end':2147483647,'plan_json':json.dumps({'code':'setup-only','name':'Setup AI budget, not product or trial access','limits':SETUP_LIMITS})}
