"""Bounded preparation and acquisition; SMTP remains the existing mail service."""
import asyncio,json,uuid,time,hashlib
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from app.database.prospects import now
from app.experiments import service
from app.experiments.plan import EXPERIMENT_ID,TEMPLATES,START,END
from app.experiments.content import ai_choice,render,email_issues,VERSION,BRIEF_VERSION

def seed_templates(c):
 from app.platform.context import require_internal_mailbox
 org=require_internal_mailbox().organization_id
 for key in TEMPLATES:c.execute("INSERT INTO email_templates(id,name,category,subject,body_text,updated_at,organization_id) VALUES(?,?,?,'Managed experiment subject','Managed evidence substitutions',?,?) ON CONFLICT DO NOTHING",(key,key.replace('_',' ').title(),'Experiment',now(),org))

def can_send(c,eid):
 return False  # Read-only history never authorizes sending.

def send_gate(c,body,*,reserved=False):
 from app.experiments.plan import in_window
 m=c.execute('SELECT * FROM experiment_members WHERE id=?',(body.get('experiment_member_id'),)).fetchone()
 if not m or m['controlled_acceptance']:raise HTTPException(409,'Controlled acceptance requires its explicit owner-only envelope override.')
 # This message is already counted after its reservation; zero remaining then
 # means it was the final permitted message, not that its reservation is invalid.
 cap=service.capacity(c)
 if not can_send(c,m['experiment_id']) and not(reserved and cap['remaining_allowance']==0 and cap['counted_last24h']<=cap['daily_capacity_ceiling'] and cap['account_wide_count_fresh'] and cap['smtp_account_authenticated'] and cap['full_daily_target_fits'] and c.execute("SELECT 1 FROM experiments WHERE id=? AND status='LIVE' AND send_approved=1",(m['experiment_id'],)).fetchone()):raise HTTPException(409,'Experiment sending is held by activation or provider capacity.')
 if not in_window(datetime.now(timezone.utc),m['recipient_timezone']):raise HTTPException(409,'Wait for the recipient-local 09:30–16:30 weekday window.')

def quality_issues(c,pid,body,data):
 from app.experiments.brief import issues
 errors=issues(data);mid=body.get('experiment_member_id');m=c.execute('SELECT * FROM experiment_members WHERE id=? AND prospect_id=?',(mid,pid)).fetchone()
 if not m:return errors+['Reviewed experiment attribution is required.']
 frozen=data.get('experiment',{})
 if frozen.get('member_id')!=mid or frozen.get('template_id')!=m['template_id'] or body.get('template_id')!=m['template_id'] or m['report_id']!=body.get('report_id'):errors.append('Immutable brief/template attribution mismatch.')
 if body.get('campaign_id')!=m['campaign_id'] or body.get('to_address')!=m['recipient']:errors.append('Campaign/recipient attribution mismatch.')
 errors.extend(email_issues(data,body))
 catalog=json.loads(m['catalog_snapshot_json'] or '{}')
 if body.get('catalog_snapshot',{})!=catalog:errors.append('Regenerate the reviewed catalog snapshot.')
 from app.reports.data import brand_config
 current=brand_config(c).get('configuration_revision')
 if current and current!=data.get('brand',{}).get('configuration_revision'):errors.append('Approved brand configuration changed; regenerate the brief.')
 return errors

def catalog_attachment(c,pid,body):
 from app.storage import artifact_storage
 from io import BytesIO
 from pypdf import PdfReader
 r=c.execute('SELECT catalog_snapshot_json FROM experiment_members WHERE id=? AND prospect_id=?',(body.get('experiment_member_id'),pid)).fetchone()
 if not r:raise HTTPException(409,'Catalog requires an attributed experiment message.')
 expected=json.loads(r[0]);provided=body.get('catalog_snapshot',{})
 if expected!=provided or not expected.get('catalog_attached'):raise HTTPException(409,'Catalog does not match the reviewed snapshot.')
 with artifact_storage().get(expected['object_key']) as stream:content=stream.read(4_000_001)
 if len(content)>4_000_000 or hashlib.sha256(content).hexdigest()!=expected['sha256']:raise HTTPException(409,'Catalog version changed or exceeded its size bound.')
 reader=PdfReader(BytesIO(content))
 if reader.is_encrypted:raise HTTPException(422,'Encrypted catalog cannot be attached.')
 return content

def ensure_run(c,eid,cid,actor):
 from app.prospecting.policy import unavailable
 unavailable()

def prepare_run(c,rid):
 from app.prospecting.policy import unavailable
 unavailable()

async def source_start(c,x,segment,exp):
 from app.prospecting.policy import unavailable
 unavailable()

async def tick(c):
 return  # Archive: no provider, assessment or send jobs.

TERMINAL={'COMPLETED','FAILED','DEGRADED','CANCELLED','BLOCKED','NEEDS_REVIEW'}

def create_schedule(c,x,segment,actor,eid):
 """Visible once-only schedules; the experiment dispatcher owns their bounded handoff."""
 sid=str(uuid.uuid5(uuid.NAMESPACE_URL,'experiment-schedule:'+x['id']))
 due=datetime.now(timezone.utc).isoformat() if segment['acquisition_date']==START else segment['acquisition_date']+'T03:30:00+00:00'
 body={'kind':'SCAN','name':f"Experiment D{segment['day']} · {segment['city']} · {x['source_type']}",'scan_source':x['source_type'],'target':x['target'],'countries':[segment['country']],'cities':[segment['city']],'verticals':[segment['vertical']],'rotate_locations':False,'rotate_verticals':False,'email_all_eligible':False,'experiment_id':eid,'experiment_source_id':x['id'],'experiment_day':segment['day'],'window_start':'09:30','window_end':'16:30','recipient_timezone':True}
 if x['source_type']=='FIRECRAWL':body['ai_prompt']=f"Find {x['target']} {segment['vertical'].replace('_',' ')} businesses in {segment['city']}, {segment['country']}, with official website and publicly evidenced business email."
 c.execute("INSERT INTO automation_schedules(id,name,kind,enabled,configuration_json,timezone,frequency,start_at,next_run_at,created_by,created_at,updated_at) VALUES(?,?,'SCAN',1,?,'Asia/Kolkata','once',?,?,?,?,?) ON CONFLICT(id) DO NOTHING",(sid,body['name'],json.dumps(body),due,due,actor,now(),now()))
 c.execute('UPDATE experiment_sources SET schedule_id=? WHERE id=?',(sid,x['id']))
 return sid

def create_schedules(c,eid,actor):
 for raw in c.execute('SELECT x.*,s.day,s.city,s.country,s.vertical,s.acquisition_date FROM experiment_sources x JOIN experiment_segments s ON s.id=x.segment_id WHERE s.experiment_id=?',(eid,)).fetchall():
  r=dict(raw);create_schedule(c,r,r,actor,eid)

def source_scheduled(c,x):
 sid=x.get('schedule_id')
 if not sid:return
 schedule=c.execute('SELECT next_run_at FROM automation_schedules WHERE id=?',(sid,)).fetchone()
 if schedule and schedule[0]:
  c.execute("INSERT INTO automation_schedule_runs(id,schedule_id,workflow_run_id,due_at,status,started_at) VALUES(?,?,?,?,'RUNNING',?) ON CONFLICT(schedule_id,due_at) DO NOTHING",(str(uuid.uuid4()),sid,x.get('workflow_id'),schedule[0],now()))
  c.execute('UPDATE automation_schedules SET next_run_at=NULL,last_run_at=?,updated_at=? WHERE id=?',(now(),now(),sid))

def reconcile_allocations(c,eid):
 """At most one bounded supplement per source/segment, capped at70/30 and100 total."""
 exp=service.get(c,eid)
 for raw in c.execute('SELECT * FROM experiment_segments WHERE experiment_id=?',(eid,)).fetchall():
  segment=dict(raw);sources=[dict(r) for r in c.execute('SELECT * FROM experiment_sources WHERE segment_id=?',(segment['id'],)).fetchall()]
  counts={source:c.execute('SELECT COUNT(*) FROM experiment_members WHERE segment_id=? AND acquisition_source=? AND controlled_acceptance=0',(segment['id'],source)).fetchone()[0] for source in ('OVERTURE','FIRECRAWL')}
  total=sum(counts.values());done=all(r['status'] in TERMINAL for r in sources)
  reason=None
  if done and total<100:
   winner=max(counts,key=counts.get);loser='FIRECRAWL' if winner=='OVERTURE' else 'OVERTURE'
   supplement=min(100-total,70-counts[winner])
   if counts[winner]>=50 and counts[loser]<50 and supplement>0 and not any(r['allocation_round']==1 for r in sources):
    xid=str(uuid.uuid5(uuid.NAMESPACE_URL,segment['id']+winner+':fallback'));c.execute("INSERT INTO experiment_sources(id,segment_id,source_type,target,allocation_round) VALUES(?,?,?,?,1) ON CONFLICT DO NOTHING",(xid,segment['id'],winner,supplement))
    create_schedule(c,{'id':xid,'source_type':winner,'target':supplement},segment,exp['created_by'],eid)
    done=False;reason=f"{loser} bounded allocation exhausted; one {supplement}-lead {winner} supplement, maximum70/30."
   else:reason=f"Bounded source allocations exhausted; {100-total} usable leads remain unfilled. No unbounded retries."
  status='COMPLETED' if total>=100 else 'SHORTFALL' if done else 'RUNNING' if any(r['status']!='PLANNED' for r in sources) else 'PLANNED'
  c.execute('UPDATE experiment_segments SET actual_source_mix=?,shortfall_reason=?,status=? WHERE id=?',(json.dumps(counts),reason,status,segment['id']))
  for source in sources:
   if source['schedule_id'] and source['status'] in TERMINAL:c.execute('UPDATE automation_schedule_runs SET status=?,completed_at=? WHERE schedule_id=? AND completed_at IS NULL',(source['status'],now(),source['schedule_id']))

async def prepare_copies(c,exp,*,force_flush=False):
 from app.prospecting.policy import unavailable
 unavailable()
