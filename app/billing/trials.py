"""Owner-approved non-chargeable trial; no subscription, mandate or paid allowances."""
import json,time,uuid
from pathlib import Path
from fastapi import HTTPException
from app.database.prospects import now
from app.accounts import policy
from app.api.organization import membership_role

POLICY=json.loads(Path(__file__).with_name('launch_trial_policy.json').read_text())

def allocate(c,actor,org):
    if membership_role(c,actor,org)!='OWNER':raise HTTPException(403,'Only the verified new workspace owner can initialize its trial.')
    from app.billing.subscription_access import enroll
    if enroll(c,actor,org):
        return {'trial_started':False,'payment_required':True,'reason':'Complete Step 5. A 72-hour trial starts only after hosted card and recurring authorization are provider-confirmed.'}
    domain=policy.company_domain(actor)
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691948020)')
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    prior=c.execute('SELECT * FROM launch_trial_claims WHERE user_id=? OR company_domain=?',(actor,domain)).fetchall()
    if prior:
        # A second verified employee/domain does not gain another trial. They can
        # accept an explicit invitation or purchase access to their own workspace.
        return {'trial_started':False,'reason':'A trial has already been used for this verified account or company domain.'}
    key=str(uuid.uuid4());stamp=int(time.time());end=stamp+POLICY['duration_days']*86400;created=now()
    snapshot={'code':'trial','name':'Seven-day trial','version':POLICY['version'],'limits':POLICY['limits'],'price_minor':0,'charge_currency':None,'automatic_renewal':False}
    c.execute('INSERT INTO launch_trial_claims(id,user_id,company_domain,organization_id,policy_version,claimed_at) VALUES(?,?,?,?,?,?)',(key,actor,domain,org,POLICY['version'],created))
    c.execute("INSERT INTO access_periods(id,organization_id,source_kind,source_id,plan_code,plan_json,status,paid_start,paid_end,verified_at,mode,created_at,updated_at) VALUES(?,?,'TRIAL',?,'trial',?,'ACTIVE',?,?,?,'trial',?,?)",(str(uuid.uuid4()),org,key,json.dumps(snapshot,sort_keys=True),stamp,end,created,created,created))
    return {'trial_started':True,'starts_at':stamp,'expires_at':end,'limits':POLICY['limits']}
