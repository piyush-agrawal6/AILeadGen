"""One attribution ledger; rates use actual sends, never open signals as success."""
import json
from collections import defaultdict,Counter
from app.experiments.service import get,capacity
from app.experiments.plan import EXPERIMENT_ID,TEMPLATES

def dashboard(c,eid=EXPERIMENT_ID):
 experiment=get(c,eid);members=[dict(r) for r in c.execute('SELECT a.*,m.status message_status,m.sent_at actual_sent_at,m.created_at message_created_at FROM experiment_members a LEFT JOIN email_messages m ON m.id=a.message_id WHERE a.experiment_id=? AND a.controlled_acceptance=0',(eid,)).fetchall()]
 ids={m['message_id'] for m in members if m['message_id']};events=defaultdict(set)
 if ids:
  for row in c.execute('SELECT message_id,event_type FROM email_engagement_events WHERE message_id IN ('+','.join('?' for _ in ids)+')',list(ids)).fetchall():events[row['message_id']].add(row['event_type'])
 def metrics(rows):
  sent=[r for r in rows if r['message_status']=='SENT'];replies=[r for r in sent if r['reply_disposition']!='OUT_OF_OFFICE' and (r['reply_disposition']!='UNKNOWN' or 'REPLIED_VERIFIED' in events[r['message_id']])]
  result={'contactable_found':len(rows),'analyzed':len(rows),'prepared':sum(bool(r['prepared_at']) for r in rows),'queued':sum(r['state']=='QUEUED' for r in rows),'sent':len(sent),'delivered_confirmed':sum('DELIVERED' in events[r['message_id']] for r in sent),'hard_bounced':sum('BOUNCED_HARD' in events[r['message_id']] for r in sent),'replies':len(replies),'positive_replies':sum(r['reply_disposition']=='POSITIVE' for r in sent),'meetings':sum(r['conversion_status']=='MEETING' for r in sent),'proposal_requests':sum(r['conversion_status']=='PROPOSAL_REQUESTED' for r in sent),'wins':sum(r['conversion_status']=='WON' for r in sent),'unsubscribes':sum('UNSUBSCRIBED' in events[r['message_id']] or r['reply_disposition']=='UNSUBSCRIBE' for r in sent)}
  result['delivery_note']='SMTP acceptance is not proof of delivery; confirmed delivery is shown only when supported by a delivery event.'
  for field,label in [('replies','reply_rate'),('positive_replies','positive_reply_rate'),('meetings','meeting_rate')]:result[label]=round(result[field]/len(sent)*100,2) if sent else None
  return result
 def grouped(keys,rows=None):
  groups=defaultdict(list)
  for m in members if rows is None else rows:groups[tuple(m[k] for k in keys)].append(m)
  return [{**dict(zip(keys,key)),**metrics(rows)} for key,rows in sorted(groups.items())]
 sources=[dict(r) for r in c.execute('SELECT x.*,s.day,s.city,s.country,s.vertical,s.planned_source_mix,s.actual_source_mix,s.shortfall_reason,j.counts_json source_counts_json,COALESCE(q.searches,0) provider_searches,COALESCE(q.scrapes,0) provider_scrapes,q.credits_used provider_credits_used,COALESCE(p.discovered,0) source_discovered,COALESCE(p.analyzed,0) source_analyzed FROM experiment_sources x JOIN experiment_segments s ON s.id=x.segment_id LEFT JOIN acquisition_jobs j ON j.id=x.acquisition_job_id LEFT JOIN (SELECT job_id,SUM(CASE WHEN kind=? THEN 1 ELSE 0 END) searches,SUM(CASE WHEN kind=? THEN 1 ELSE 0 END) scrapes,SUM(credits) credits_used FROM acquisition_requests GROUP BY job_id) q ON q.job_id=x.acquisition_job_id LEFT JOIN (SELECT campaign_id,SUM(raw_found) discovered,SUM(websites_processed) analyzed FROM pipeline_runs GROUP BY campaign_id) p ON p.campaign_id=x.campaign_id WHERE s.experiment_id=? ORDER BY s.day,s.city,x.source_type',('search','scrape',eid)).fetchall()]
 daily=[]
 for day in range(1,6):
  subset=[m for m in members if m['experiment_day']==day];measures=metrics(subset)
  def best(key,worst=False):
   candidates=[g for g in grouped((key,),subset) if g['sent']>0]
   choose=min if worst else max
   return choose(candidates,key=lambda r:(r['positive_reply_rate'],r['meeting_rate']))[key] if candidates else None
  daily.append({'day':day,'date':f'2026-11-{day+1:02}','target':500,**measures,'best_source':best('acquisition_source'),'best_template':best('template_id'),'worst_template':best('template_id',True),'best_vertical':best('vertical'),'best_market':best('city'),'best_pitch':best('primary_pitch'),'bounce_outliers':[r for r in grouped(('template_id',),subset) if r['sent']>=10 and r['hard_bounced']/r['sent']>=.2],'unsubscribe_outliers':[r for r in grouped(('template_id',),subset) if r['unsubscribes']>0],'shortfall':max(0,500-len(subset))})
 source_metrics=[{'acquisition_source':source,**metrics([m for m in members if m['acquisition_source']==source])} for source in ('OVERTURE','FIRECRAWL')]
 for group in source_metrics:
  relevant=[s for s in sources if s['source_type']==group['acquisition_source']];group['discovered']=0;group['resource_usage']={'searches':0,'scraped_pages':0,'audited_websites':0}
  for source in relevant:
   counts=json.loads(source['source_counts_json'] or '{}');group['discovered']+=counts.get('businesses_found',counts.get('candidates',0)) if source['acquisition_job_id'] else source['source_discovered'];group['resource_usage']['searches']+=source['provider_searches'];group['resource_usage']['scraped_pages']+=source['provider_scrapes'];group['resource_usage']['audited_websites']+=source['source_analyzed']
 return {'experiment':experiment,'totals':{'target':2500,**metrics(members)},'daily':daily,'sources':source_metrics,'templates':[{**{'template_id':t},**metrics([m for m in members if m['template_id']==t])} for t in TEMPLATES],'pitches':grouped(('primary_pitch',)),'verticals':grouped(('vertical',)),'markets':grouped(('country','city')),'segments':sources,'provider_capacity':capacity(c),'resource_usage_note':'Provider request ledger counts attempts, including uncertain results. Unrecorded credits or monetary cost are not estimated.','allocation_policy':'Fixed eligible-strategy allocation within source/market strata; no early winner optimization. Ineligible strategies are recorded, never fabricated.'}
