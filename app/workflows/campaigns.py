"""One campaign audience/accounting implementation for manual and scheduled outreach."""
import json
from collections import Counter
from fastapi import HTTPException
from app.mail.service import address
from app.mail.contacted import known_addresses

SCOPE="SELECT qb.prospect_id FROM businesses qb JOIN pipeline_runs qr ON qr.id=qb.run_id WHERE qr.campaign_id=? AND qb.processing_status='QUALIFIED'"

AUDIENCE_ROWS_SQL="""SELECT b.*,b.id business_id,p.lead_status,p.first_seen_at,p.assigned_to,
 m.contact_state,m.sales_state,m.manual_reason,s.suppressed_at,s.last_contact_at,i.commercial_fit,i.business_scale,
 o.primary_opportunity,o.website_opportunity_score,o.seo_opportunity_score,o.security_opportunity_score,o.evidence_json
 FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id JOIN prospects p ON p.id=b.prospect_id
 LEFT JOIN master_lead_state m ON m.prospect_id=p.id LEFT JOIN prospect_sales s ON s.prospect_id=p.id
 LEFT JOIN business_intelligence i ON i.business_id=b.id LEFT JOIN opportunity_scores o ON o.business_id=b.id
 WHERE r.campaign_id=? AND b.processing_status='QUALIFIED'
 AND b.id=(SELECT MAX(b2.id) FROM businesses b2 JOIN pipeline_runs r2 ON r2.id=b2.run_id WHERE b2.prospect_id=b.prospect_id AND r2.campaign_id=? AND b2.processing_status='QUALIFIED')
 ORDER BY b.name,b.prospect_id"""

def campaign_org(c,cid):
 from app.platform.context import organization
 org=organization()
 r=c.execute('SELECT organization_id FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,org)).fetchone()
 return r['organization_id'] if r else None

def campaign(c,cid,_batch=None,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 r=_batch['campaigns'].get(cid) if _batch else c.execute('SELECT * FROM scan_campaigns WHERE id=?'+(' AND organization_id=?' if organization else ''),(cid,)+((organization,) if organization else ())).fetchone()
 if not r:raise HTTPException(404,'Choose an existing campaign.')
 result=dict(r);options=json.loads(result['configuration_json'])
 result['name']=options.get('name') or (' / '.join(options.get('cities') or [])+' · '+' / '.join(options.get('verticals') or [])) or 'Campaign '+cid[:8]
 result['configuration']=options
 result['source_type']=result.get('source_type','OVERTURE');result['source_metadata']=json.loads(result.get('source_metadata') or '{}')
 from app.acquisition.policy import policy
 result['processing_policy']=policy(result['source_type']).mode.value;result['processing_mode']=policy(result['source_type']).label
 org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 runs=_batch['scans'].get(cid,[]) if _batch else [dict(r) for r in c.execute('SELECT id,market,vertical,status,target,started_at,finished_at,raw_found,websites_processed,filtered,qualified,error_message FROM pipeline_runs WHERE campaign_id=?'+org_sql+' ORDER BY id',(cid,)+org_args).fetchall()]
 owner=_batch['owners'].get(cid) if _batch else c.execute("SELECT name,status,completed_at FROM workflow_runs WHERE id=? AND kind IN ('SCAN','COMBINED')"+org_sql,(cid,)+org_args).fetchone()
 if owner:result['name']=owner['name']
 result['status']=owner['status'] if owner else 'RUNNING' if any(r['status'] in ('QUEUED','RUNNING') for r in runs) else 'COMPLETED' if runs and all(r['status']=='COMPLETED' for r in runs) else 'FAILED' if any(r['status'] in ('FAILED','INTERRUPTED') for r in runs) else result['status']
 result['completed_at']=(owner['completed_at'] if owner else None) or result['completed_at']
 result['scans']=runs;result['markets']=list(dict.fromkeys(r['market'] for r in runs));result['verticals']=list(dict.fromkeys(r['vertical'] for r in runs))
 result['raw_found']=sum(r['raw_found'] or 0 for r in runs);result['analyzed']=sum(r['websites_processed'] or 0 for r in runs)
 return result

def audience(c,cid,pitch_types=None,mode='UNCONTACTED',*,run_id=None,require_complete=False,_batch=None,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 info=campaign(c,cid,_batch,organization=organization)
 if require_complete and info['configuration'].get('qualification_mode')!='CONTACTABLE_ONLY' and info['status'] in ('RUNNING','QUEUED','PAUSED','DRAFT','PREPARING'):raise HTTPException(409,'Finish or stop the scan before reviewing its outreach audience.')
 selected=[]  # Legacy pitch inputs never gate general-purpose campaign eligibility.
 rows=[dict(r) for r in _batch['rows'].get(cid,[])] if _batch else [dict(r) for r in c.execute(AUDIENCE_ROWS_SQL,(cid,cid)).fetchall()]
 # Bounded round trips, independent of campaign size. No N+1 recipient queries.
 org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 blocked=_batch['blocked'] if _batch else {r['address'].lower():r['status'] for r in c.execute("SELECT address,status FROM email_address_suppressions WHERE status IN ('INVALID','TEMPORARILY_UNUSABLE')"+org_sql,org_args).fetchall()}
 emails={}
 sql="SELECT b.prospect_id,b.public_email email FROM businesses b WHERE b.prospect_id IN ("+SCOPE+") AND b.public_email IS NOT NULL UNION SELECT b.prospect_id,x.contact_value email FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id IN ("+SCOPE+") AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1"
 pids={b['prospect_id'] for b in rows}
 for r in (_batch['emails'] if _batch else c.execute(sql,(cid,cid)).fetchall()):
  if r['prospect_id'] not in pids:continue
  try:email=address(r['email'])
  except HTTPException:continue
  if email not in blocked:emails.setdefault(r['prospect_id'],set()).add(email)
 sent=set();uncertain=set();last_touch={}
 for r in (_batch['messages'] if _batch else c.execute("SELECT prospect_id,status,sent_at,created_at FROM email_messages WHERE prospect_id IN ("+SCOPE+") AND direction='OUTBOUND' AND test_mode=0 AND message_type<>'OWNER_CONTROLLED_REDIRECT' AND status IN ('SENT','SENDING','UNCERTAIN')",(cid,)).fetchall()):
  if r['prospect_id'] not in pids:continue
  if r['status']=='SENT':sent.add(r['prospect_id'])
  else:uncertain.add(r['prospect_id'])
  last_touch[r['prospect_id']]=max(last_touch.get(r['prospect_id'],''),r['sent_at'] or r['created_at'])
 hard=set();soft=set();replied=set();unsub=set()
 for r in (_batch['events'] if _batch else c.execute("SELECT e.prospect_id,e.event_type FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.prospect_id IN ("+SCOPE+") AND m.test_mode=0 AND e.event_type IN ('BOUNCED_HARD','BOUNCED_SOFT','REPLIED_VERIFIED','UNSUBSCRIBED')",(cid,)).fetchall()):
  if r['prospect_id'] not in pids:continue
  {'BOUNCED_HARD':hard,'BOUNCED_SOFT':soft,'REPLIED_VERIFIED':replied,'UNSUBSCRIBED':unsub}[r['event_type']].add(r['prospect_id'])
 reserved={}
 for r in (_batch['reservations'] if _batch else c.execute("SELECT i.prospect_id,i.run_id,i.status,r.status run_status FROM outreach_run_items i JOIN workflow_runs r ON r.id=i.run_id WHERE i.prospect_id IN ("+SCOPE+") AND r.status IN ('RUNNING','PAUSED','DRAFT','PREPARING','NEEDS_REVIEW') AND i.status IN ('QUEUED','READY','PREPARING','SENDING')",(cid,)).fetchall()):
  if r['prospect_id'] not in pids:continue
  if r['run_id']!=run_id:reserved[r['prospect_id']]=r['run_status']
 from app.workflows.configuration import load
 policy=_batch['pitch_policy'] if _batch else {k:v.model_dump() for k,v in load(c,organization).pitches.items()}
 trusted=_batch['trusted'] if _batch else trusted_emails(c,[cid],organization=organization)
 contacted_addresses=_batch['contacted_addresses'] if _batch else known_addresses(c,[e for values in emails.values() for e in values])
 counts=Counter();items=[]
 for b in rows:
  pid=b['prospect_id'];status='READY';reason=None;known=sorted(emails.get(pid,set()));usable=[e for e in known if (pid,e) in trusted]
  previously_contacted_addresses=[e for e in usable if e in contacted_addresses]
  usable=[e for e in usable if e not in previously_contacted_addresses]
  evidence=json.loads(b.get('evidence_json') or '{}')
  data={'mode':'REACHABLE' if b['website_status']=='REACHABLE' else 'NO_WEBSITE' if not b['website'] else 'UNREACHABLE','primary':b['primary_opportunity'],'scores':{k:b.get(col) for k,col in [('WEBSITE','website_opportunity_score'),('SEO','seo_opportunity_score'),('SECURITY','security_opportunity_score')]},'evidence':evidence}
  data['pitch_policy']=policy
  supported=['WORKSPACE']
  if b['is_rejected'] or b['suppressed_at'] or b['lead_status'] in ('DO_NOT_CONTACT','NOT_INTERESTED','WON','LOST') or b['contact_state'] in ('DO_NOT_CONTACT','UNSUBSCRIBED') or b['sales_state'] in ('REJECTED','NOT_INTERESTED','WON','LOST') or pid in hard|unsub:
   status='SUPPRESSED';reason='DNC, unsubscribe, hard bounce, rejection or closed sales state.'
  elif pid in replied or b['lead_status'] in ('REPLIED','MEETING','PROPOSAL') or b['sales_state'] in ('REPLIED','MEETING','PROPOSAL') or b['contact_state']=='REPLIED':status='REPLIED';reason='An active conversation must not receive automated first-contact outreach.'
  elif previously_contacted_addresses and not usable:status='ALREADY_CONTACTED';reason='This organization has already emailed this exact address.'
  elif pid in uncertain:status='NEEDS_REVIEW';reason='An earlier SMTP result is uncertain. Never automatically retry.'
  elif pid in reserved:status='QUEUED_ELSEWHERE';reason='Already reserved by another open email run.'
  elif b['manual_reason']=='Owner requested manual contact':status='MANUAL_CONTACT';reason='Owner requested manual contact.'
  elif b['contact_state']=='NEEDS_REVIEW' and b['manual_reason']=='Owner requested review':status='NEEDS_REVIEW';reason='Owner requested manual verification.'
  elif not usable and known:status='NEEDS_REVIEW';reason='Email source or domain validation is uncertain. Review contact evidence before outreach.'
  elif not usable:status='MANUAL_CONTACT';reason='No usable public email. Phone/social contact remains available.'
  elif b['contact_state'] in ('CONNECTED_MANUALLY','EMAIL_BOUNCED') or pid in soft:status='NEEDS_REVIEW';reason='Existing contact or temporary delivery condition requires review.'
  elif pid in sent and mode!='RECONTACT':status='ALREADY_CONTACTED';reason='Previously contacted; explicit re-contact confirmation is required.'
  elif not supported:status='NEEDS_REVIEW';reason='Review the workspace template before preparing outreach.'
  b.update(campaign_id=cid,campaign_name=info['name'],disposition=status,reason=reason,recipient=usable[0] if usable else None,pitch_types=supported,previously_contacted=pid in sent,last_contact_at=last_touch.get(pid) or b['last_contact_at'])
  b.pop('evidence_json',None);items.append(b);counts[status]+=1
 accounting={'ready':counts['READY'],'queued':counts['QUEUED_ELSEWHERE'],'sent':counts['ALREADY_CONTACTED'],'replied':counts['REPLIED'],'manual_contact':counts['MANUAL_CONTACT'],'needs_review':counts['NEEDS_REVIEW'],'suppressed':counts['SUPPRESSED']}
 return {'campaign':info,'items':items,'qualified':len(items),'email_eligible':sum(bool(b['recipient']) and b['disposition'] not in ('SUPPRESSED','REPLIED','NEEDS_REVIEW') for b in items),'already_contacted':len(sent),'will_queue':counts['READY'],'manual_contact':counts['MANUAL_CONTACT'],'suppressed':counts['SUPPRESSED'],'needs_review':counts['NEEDS_REVIEW'],'replied':counts['REPLIED'],'bounced':len(hard|soft),'remaining_uncontacted':sum(b['prospect_id'] not in sent for b in items),'accounting':accounting,'total_accounted':sum(accounting.values()),'pitch_types':selected}

def campaign_summary(c,cid,_batch=None,organization=None):
 a=audience(c,cid,_batch=_batch,organization=organization);info=a.pop('campaign');a.pop('items')
 info.update(a);info['shortfall']=max(0,info['target_total']-a['qualified'])
 org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 info['outreach_runs']=[{**dict(r),'configuration':json.loads(r['configuration_json'])} for r in (_batch['outreach'].get(cid,[]) if _batch else c.execute("SELECT * FROM workflow_runs WHERE campaign_id=?"+org_sql+" AND kind='OUTREACH' ORDER BY created_at DESC",(cid,)+org_args).fetchall())]
 info['last_activity']=max([info.get('completed_at') or info['created_at'],*[r.get('completed_at') or r.get('started_at') or r['created_at'] for r in info['outreach_runs']]])
 return info

def batch_data(c,cids,organization=None):
 """One bounded set of queries per page, using the same audience classifier."""
 from collections import defaultdict
 from app.workflows.configuration import load
 if not cids:return None
 marks=','.join('?' for _ in cids);scope=SCOPE.replace('qr.campaign_id=?','qr.campaign_id IN ('+marks+')')
 org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 result={'campaigns':{r['id']:dict(r) for r in c.execute('SELECT * FROM scan_campaigns WHERE id IN ('+marks+')'+org_sql,[*cids,*org_args]).fetchall()},'scans':defaultdict(list),'outreach':defaultdict(list),'owners':{},'rows':defaultdict(list)}
 for r in c.execute('SELECT * FROM pipeline_runs WHERE campaign_id IN ('+marks+')'+org_sql+' ORDER BY id',[*cids,*org_args]).fetchall():result['scans'][r['campaign_id']].append(dict(r))
 for r in c.execute('SELECT * FROM workflow_runs WHERE (campaign_id IN ('+marks+') OR id IN ('+marks+'))'+org_sql+' ORDER BY created_at DESC',[*cids,*cids,*org_args]).fetchall():
  if r['kind']=='OUTREACH':result['outreach'][r['campaign_id']].append(dict(r))
  elif r['id'] in cids:result['owners'][r['id']]=dict(r)
 sql=AUDIENCE_ROWS_SQL.replace('SELECT b.*,','SELECT r.campaign_id campaign_scope,b.*,',1).replace('WHERE r.campaign_id=?','WHERE r.campaign_id IN ('+marks+')').replace('r2.campaign_id=?','r2.campaign_id=r.campaign_id')
 for r in c.execute(sql,cids).fetchall():result['rows'][r['campaign_scope']].append(dict(r))
 result['blocked']={r['address'].lower():r['status'] for r in c.execute("SELECT address,status FROM email_address_suppressions WHERE status IN ('INVALID','TEMPORARILY_UNUSABLE')"+org_sql,org_args).fetchall()}
 result['emails']=c.execute("SELECT b.prospect_id,b.public_email email FROM businesses b WHERE b.prospect_id IN ("+scope+") AND b.public_email IS NOT NULL UNION SELECT b.prospect_id,x.contact_value email FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id IN ("+scope+") AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1",[*cids,*cids]).fetchall()
 result['contacted_addresses']=known_addresses(c,[r['email'] for r in result['emails']])
 result['messages']=c.execute("SELECT prospect_id,status,sent_at,created_at FROM email_messages WHERE prospect_id IN ("+scope+") AND direction='OUTBOUND' AND test_mode=0 AND message_type<>'OWNER_CONTROLLED_REDIRECT' AND status IN ('SENT','SENDING','UNCERTAIN')",cids).fetchall()
 result['events']=c.execute("SELECT e.prospect_id,e.event_type FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.prospect_id IN ("+scope+") AND m.test_mode=0 AND e.event_type IN ('BOUNCED_HARD','BOUNCED_SOFT','REPLIED_VERIFIED','UNSUBSCRIBED')",cids).fetchall()
 result['reservations']=c.execute("SELECT i.prospect_id,i.run_id,i.status,r.status run_status FROM outreach_run_items i JOIN workflow_runs r ON r.id=i.run_id WHERE i.prospect_id IN ("+scope+") AND r.status IN ('RUNNING','PAUSED','DRAFT','PREPARING','NEEDS_REVIEW') AND i.status IN ('QUEUED','READY','PREPARING','SENDING')",cids).fetchall()
 result['pitch_policy']={k:v.model_dump() for k,v in load(c,organization).pitches.items()}
 result['trusted']=trusted_emails(c,cids,source_schema=any('source_type' in r for r in result['campaigns'].values()),organization=organization)
 return result


def trusted_emails(c,cids,*,source_schema=None,organization=None):
 from app.acquisition.policy import valid_email
 if not cids:return set()
 if source_schema is None:
  from app.database.acquisition_schema import ready
  source_schema=ready(c)
 marks=','.join('?' for _ in cids)
 scope="SELECT b.prospect_id FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id IN ("+marks+")"+(" AND r.organization_id=?" if organization else "")
 base_args=list(cids)+([organization] if organization else [])
 sql="SELECT DISTINCT b.prospect_id,LOWER(x.contact_value) email,NULL fields FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id IN ("+scope+") AND x.contact_type='email' AND x.is_public_business_contact=1 AND x.is_valid=1 AND x.source_url IS NOT NULL AND x.source_url<>''"
 args=list(base_args)
 if source_schema:
  sql+=" UNION ALL SELECT b.prospect_id,LOWER(b.public_email) email,e.field_sources_json fields FROM lead_source_evidence e JOIN businesses b ON b.id=e.business_id WHERE b.prospect_id IN ("+scope+") AND e.source_type IN ('FILE_IMPORT','GOOGLE_SHEETS')"+(" AND e.organization_id=?" if organization else "")+" AND b.processing_status='QUALIFIED'"
  args+=list(base_args)+([organization] if organization else [])
 result=set()
 for row in c.execute(sql,args).fetchall():
  email=valid_email(row['email'])
  if not email:continue
  if row['fields']:
   evidence=json.loads(row['fields']).get('email') or {}
   if evidence.get('verification')!='OWNER_PROVIDED' or valid_email(evidence.get('value'))!=email:continue
  result.add((row['prospect_id'],email))
 return result
