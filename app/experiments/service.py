"""Experiment metadata and eligibility; existing canonical/mail state stays authoritative."""
import json,uuid,hashlib,re
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from app.database.prospects import now
from app.database.experiment_schema import ready
from app.experiments.plan import EXPERIMENT_ID,NAME,START,END,DAILY_TARGET,TOTAL_TARGET,segments,TEMPLATES

GATES=('backend','frontend','postgres','brief_visual','full_pdf','five_controlled_emails','controlled_reply','source_overture','source_firecrawl','schedule','suppression','provider_capacity','smtp','inbox_sync','dashboard','ai_provider')

def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),default=str)
def event(c,eid,kind,metadata=None,key=None):
 c.execute('INSERT INTO experiment_events(id,experiment_id,event_type,metadata_json,created_at,dedup_key) VALUES(?,?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',(str(uuid.uuid4()),eid,kind,encoded(metadata or {}),now(),key))
def setup(c,actor):
 if not ready(c):raise HTTPException(503,'Experiment schema has not been deployed.')
 config={'sender':'PlaneByte <planebyte@gmail.com>','daily_source_targets':{'OVERTURE':250,'FIRECRAWL':250},'window_start':'09:30','window_end':'16:30','timezone':'Asia/Kolkata','catalog':'OFF','auto_reply':False,'allocation_adaptive':False,'provider_daily_ceiling':500,'batch_size':25}
 c.execute("INSERT INTO experiments(id,name,start_date,end_date,daily_target,total_target,status,configuration_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,'SETUP',?,?,?,?) ON CONFLICT(id) DO NOTHING",(EXPERIMENT_ID,NAME,START,END,DAILY_TARGET,TOTAL_TARGET,encoded(config),actor,now(),now()))
 for s in segments():
  sid=str(uuid.uuid5(uuid.NAMESPACE_URL,EXPERIMENT_ID+str(s['day'])+s['city']))
  c.execute('INSERT INTO experiment_segments(id,experiment_id,day,acquisition_date,country,city,vertical,recipient_timezone,target,planned_source_mix) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(experiment_id,day,city) DO NOTHING',(sid,EXPERIMENT_ID,s['day'],s['date'],s['country'],s['city'],s['vertical'],s['timezone'],100,encoded(s['sources'])))
  for source in ('OVERTURE','FIRECRAWL'):
   source_id=str(uuid.uuid5(uuid.NAMESPACE_URL,sid+source));c.execute('INSERT INTO experiment_sources(id,segment_id,source_type,target) VALUES(?,?,?,50) ON CONFLICT(segment_id,source_type,allocation_round) DO NOTHING',(source_id,sid,source))
 from app.experiments.runtime import seed_templates
 seed_templates(c)
 return get(c)
def get(c,eid=EXPERIMENT_ID):
 row=c.execute('SELECT * FROM experiments WHERE id=?',(eid,)).fetchone()
 if not row:raise HTTPException(404,'Experiment has not been configured.')
 result=dict(row);result['configuration']=json.loads(result.pop('configuration_json'));result['acceptance']=json.loads(result.pop('acceptance_json'));return result

def acceptance(c,checks,actor,eid=EXPERIMENT_ID):
 from app.api.permissions import require_owner
 require_owner(c,actor);r=get(c,eid);prior=r['acceptance']
 if any(k not in GATES for k in checks):raise HTTPException(422,'Unknown acceptance gate.')
 prior.update(checks);status='READY' if all(prior.get(k,{}).get('passed') is True for k in GATES) else 'TESTING'
 c.execute('UPDATE experiments SET acceptance_json=?,status=?,updated_at=? WHERE id=?',(encoded(prior),status,now(),eid));event(c,eid,'ACCEPTANCE_RECORDED',{'checks':list(checks),'status':status});return get(c,eid)

def capacity(c,*,settings=None,at=None):
 from app.mail.config import mail_settings
 from app.automation.settings import effective_settings
 s=effective_settings(c,settings or mail_settings());at=at or datetime.now(timezone.utc)
 # Gmail personal has no API exposing remaining sending quota. Count both app
 # reservations and visible Sent messages when the explicit preflight supplies it.
 ceiling=min(500,s.max_day) if s.provider=='gmail' and s.from_address.lower().endswith('@gmail.com') else min(500,s.max_day)
 since=(at-timedelta(hours=24)).isoformat()
 count=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENT','SENDING','UNCERTAIN') AND created_at>=?",(since,)).fetchone()[0]
 external=0;fresh=False;preflight_at=None
 if ready(c):
  r=c.execute('SELECT configuration_json FROM experiments WHERE id=?',(EXPERIMENT_ID,)).fetchone()
  if r:
   config=json.loads(r[0]);external=sum(t>=since for t in config.get('untracked_sent_at',[]));preflight_at=config.get('provider_preflight_at');fresh=bool(config.get('provider_capacity_verified') and preflight_at and at-datetime.fromisoformat(preflight_at)<timedelta(minutes=90))
 used=count+external;return {'provider':s.provider,'sender':s.from_address,'daily_capacity_ceiling':ceiling,'counted_last24h':used,'remaining_allowance':max(0,ceiling-used),'requested_daily_target':500,'full_daily_target_fits':ceiling>=500,'smtp_account_authenticated':bool(c.execute("SELECT 1 FROM email_accounts WHERE provider=? AND status='CONNECTED' AND smtp_health='READY'",(s.provider,)).fetchone()),'remaining_is_counted_not_provider_guaranteed':True,'limit_source':'https://support.google.com/mail/answer/22839?hl=en','account_wide_count_fresh':fresh,'provider_preflight_at':preflight_at,'untracked_account_sends':external,'global_max_hour':s.max_hour,'global_max_day':s.max_day}

def activate(c,actor,eid=EXPERIMENT_ID):
 from app.api.permissions import require_owner
 from app.workflows.controls import require_unpaused
 require_owner(c,actor);r=get(c,eid);missing=[k for k in GATES if not r['acceptance'].get(k,{}).get('passed')]
 if missing:raise HTTPException(409,{'message':'Experiment has not launched. Acceptance gates remain.','missing':missing})
 today=datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()
 if today!=START and not c.execute("SELECT 1 FROM experiment_sources x JOIN experiment_segments s ON s.id=x.segment_id WHERE s.experiment_id=? AND s.day=1 AND x.campaign_id IS NOT NULL",(eid,)).fetchone():raise HTTPException(409,'Day1 did not start November2. Do not silently shift this experiment; owner review required.')
 require_unpaused(c,'scan');require_unpaused(c,'email');cap=capacity(c)
 if not cap['full_daily_target_fits'] or not cap['smtp_account_authenticated'] or not cap['account_wide_count_fresh']:raise HTTPException(409,{'message':'Provider capacity/authentication blocks sending. Acquisition may be activated separately.','capacity':cap})
 from app.experiments.runtime import create_schedules
 create_schedules(c,eid,actor)
 c.execute("UPDATE experiments SET status='LIVE',send_approved=1,updated_at=? WHERE id=?",(now(),eid));event(c,eid,'ACTIVATED',{'provider_capacity':cap},eid+':activation');return get(c,eid)

def audience(c,cid,pitch_types=None,mode='UNCONTACTED',*,run_id=None,require_complete=False):
 """Reuse every global contact guard; replace only the long-report pitch gate."""
 from app.workflows.campaigns import audience as canonical
 from app.reports.data import client_snapshot
 from app.experiments.content import eligible_templates
 data=canonical(c,cid,pitch_types,mode,run_id=run_id,require_complete=False)
 for item in data['items']:
  if item['disposition']=='NEEDS_REVIEW' and str(item['reason']).startswith('None of the selected pitches has two meaningful findings'):
   # The contact was already validated before the original content gate.
   if eligible_templates(client_snapshot(c,item['business_id'],now())):item.update(disposition='READY',reason=None,pitch_types=['SEO','SECURITY','WEBSITE'])
 counts=Counter(i['disposition'] for i in data['items']);data.update(will_queue=counts['READY'],needs_review=counts['NEEDS_REVIEW']);return data

def admit(c,eid,segment,source,campaign_id,*,controlled=False):
 from app.experiments.content import assign_template,eligible_templates,pitch,VERSION
 from app.reports.data import client_snapshot
 from app.workflows.campaigns import trusted_emails
 from app.mail.service import address
 if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945602)')
 snapshot=audience(c,campaign_id);counts=Counter(r[0] for r in c.execute('SELECT template_id FROM experiment_members WHERE experiment_id=? AND segment_id=? AND acquisition_source=?',(eid,segment['id'],source)).fetchall());added=0
 limits=allocation_remaining(c,eid,segment,source) if not controlled else 5
 for b in snapshot['items']:
  if added>=limits:break
  if b['disposition']!='READY':continue
  if c.execute("SELECT 1 FROM automation_email_queue WHERE prospect_id=? AND status IN ('QUEUED','ATTEMPTING','REVIEW')",(b['prospect_id'],)).fetchone():continue
  if c.execute('SELECT 1 FROM experiment_members WHERE experiment_id=? AND prospect_id=?',(eid,b['prospect_id'])).fetchone():continue
  data=client_snapshot(c,b['business_id'],now())
  if not eligible_templates(data):continue
  email=address(b['recipient']);domain=(b.get('domain') or '').lower() or None
  if c.execute('SELECT 1 FROM experiment_members WHERE experiment_id=? AND (recipient=? OR normalized_domain=?)',(eid,email,domain)).fetchone():continue
  template=assign_template(data,eid+source+segment['city']+b['prospect_id'],counts);primary,secondary=pitch(data,template);mid=str(uuid.uuid4());subject=int(hashlib.sha256(mid.encode()).hexdigest(),16)%2
  changed=c.execute('INSERT INTO experiment_members(id,experiment_id,segment_id,experiment_day,prospect_id,business_id,campaign_id,acquisition_source,country,city,vertical,normalized_domain,recipient,recipient_timezone,template_id,template_version,subject_variant,primary_pitch,secondary_pitch,controlled_acceptance,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',(mid,eid,segment['id'],segment['day'],b['prospect_id'],b['business_id'],campaign_id,source,segment['country'],segment['city'],segment['vertical'],domain,email,segment['recipient_timezone'],template,VERSION,subject,primary,secondary,int(controlled),now())).rowcount
  if changed:counts[template]+=1;added+=1
 return added

def allocation_remaining(c,eid,segment,source):
 """Durable allocation limits, separate from the all-eligible campaign audience."""
 live=" AND controlled_acceptance=0"
 total=c.execute('SELECT COUNT(*) FROM experiment_members WHERE experiment_id=?'+live,(eid,)).fetchone()[0]
 daily=c.execute('SELECT COUNT(*) FROM experiment_members WHERE experiment_id=? AND experiment_day=?'+live,(eid,segment['day'])).fetchone()[0]
 segment_count=c.execute('SELECT COUNT(*) FROM experiment_members WHERE experiment_id=? AND segment_id=?'+live,(eid,segment['id'])).fetchone()[0]
 source_count=c.execute('SELECT COUNT(*) FROM experiment_members WHERE experiment_id=? AND segment_id=? AND acquisition_source=?'+live,(eid,segment['id'],source)).fetchone()[0]
 allocation=c.execute('SELECT COALESCE(SUM(target),0) FROM experiment_sources WHERE segment_id=? AND source_type=?',(segment['id'],source)).fetchone()[0]
 return max(0,min(2500-total,500-daily,100-segment_count,min(70,allocation)-source_count))

def message_hook(c,message_id,body):
 """Called in the existing SMTP reservation transaction, before sending."""
 member=body.get('experiment_member_id')
 if not member:return
 r=c.execute('SELECT * FROM experiment_members WHERE id=?',(member,)).fetchone()
 if not r or r['report_id']!=body.get('report_id') or r['template_id']!=body.get('template_id'):raise HTTPException(409,'Experiment attribution does not match its reviewed member.')
 c.execute('UPDATE experiment_members SET message_id=? WHERE id=?',(message_id,member))

def sync_messages(c,eid=EXPERIMENT_ID):
 for row in c.execute("SELECT a.id,a.message_id,m.status,m.sent_at FROM experiment_members a JOIN email_messages m ON m.id=a.message_id WHERE a.experiment_id=?",(eid,)).fetchall():
  c.execute('UPDATE experiment_members SET state=?,sent_at=COALESCE(?,sent_at) WHERE id=?',('SENT' if row['status']=='SENT' else 'NEEDS_REVIEW' if row['status'] in ('FAILED','UNCERTAIN') else 'SENDING',row['sent_at'],row['id']))


def reply(c,member_id,disposition,actor,*,inbound_id=None,manual=False):
 allowed=('POSITIVE','QUESTION','NOT_NOW','NEGATIVE','UNSUBSCRIBE','OUT_OF_OFFICE','UNKNOWN')
 if disposition not in allowed:raise HTTPException(422,'Choose a supported reply disposition.')
 r=c.execute('SELECT * FROM experiment_members WHERE id=?',(member_id,)).fetchone()
 if not r:raise HTTPException(404,'Experiment lead not found.')
 conversion='POSITIVE_REPLY' if disposition=='POSITIVE' else 'REPLIED'
 c.execute("UPDATE experiment_members SET reply_disposition=?,conversion_status=CASE WHEN conversion_status IN ('MEETING','PROPOSAL_REQUESTED','WON','LOST') THEN conversion_status ELSE ? END WHERE id=?",(disposition,conversion,member_id))
 if inbound_id:c.execute('INSERT INTO experiment_replies(inbound_message_id,member_id,disposition,confidence,method,manually_corrected,classified_at,corrected_by) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(inbound_message_id) DO UPDATE SET disposition=excluded.disposition,manually_corrected=excluded.manually_corrected,corrected_by=excluded.corrected_by',(inbound_id,member_id,disposition,'HIGH' if manual else 'MEDIUM','MANUAL' if manual else 'BOUNDED_RULES',int(manual),now(),actor if manual else None))
 if disposition=='UNSUBSCRIBE':
  from app.mail.tracking import event as engagement
  if r['message_id']:engagement(c,r['message_id'],'UNSUBSCRIBED',metadata={'source':'VERIFIED_REPLY_CLASSIFICATION'})
  if not r['controlled_acceptance']:
   from app.sales.service import suppressed
   c.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(r['prospect_id'],))
 event(c,r['experiment_id'],'REPLY_CLASSIFIED',{'member_id':member_id,'disposition':disposition,'manual':manual},('reply:'+inbound_id) if inbound_id and not manual else None)

def classify(text):
 # Classify the new reply, excluding quoted outreach and its opt-out footer.
 text=re.split(r'(?im)^On .+wrote:|^From:|^[-_]{3,}.*Original',text)[0]
 text='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('>')).casefold()[:10000]
 if any(v in text for v in ('unsubscribe','remove me','stop emailing','do not contact')):return 'UNSUBSCRIBE'
 if any(v in text for v in ('out of office','automatic reply','on annual leave')):return 'OUT_OF_OFFICE'
 if any(v in text for v in ('not interested','no thank you','no thanks')):return 'NEGATIVE'
 if any(v in text for v in ('not now','next quarter','later this year','get back next')):return 'NOT_NOW'
 if any(v in text for v in ('interested','send the scope','send over the approach','yes please','schedule a call','let us discuss')):return 'POSITIVE'
 if '?' in text:return 'QUESTION'
 return 'UNKNOWN'

def inbound_hook(c,outbound_id,inbound_id,text,*,automatic=False):
 r=c.execute('SELECT id FROM experiment_members WHERE message_id=?',(outbound_id,)).fetchone()
 if r and not c.execute('SELECT 1 FROM experiment_replies WHERE inbound_message_id=?',(inbound_id,)).fetchone():reply(c,r['id'],'OUT_OF_OFFICE' if automatic else classify(text),'system',inbound_id=inbound_id)
