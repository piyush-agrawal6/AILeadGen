"""Current fixed-template results; delivery requires a genuine delivery event."""
from collections import defaultdict
from app.mail.contacted import organization
from app.outreach.fixed import TEMPLATES,VERSION,ASSET_ID
from app.database.contactable_schema import ready

def summary(c):
 if not ready(c):return {'ready':False,'templates':[],'sources':[]}
 rows=[dict(r) for r in c.execute("SELECT m.id,m.template_id,m.status,m.prospect_id,s.source_type,l.sales_state FROM email_messages m LEFT JOIN scan_campaigns s ON s.id=m.campaign_id LEFT JOIN master_lead_state l ON l.prospect_id=m.prospect_id WHERE m.organization_id=? AND m.outreach_strategy='FIXED_5' AND m.direction='OUTBOUND' AND m.test_mode=0",(organization(),)).fetchall()]
 events=defaultdict(set)
 for r in c.execute("SELECT e.message_id,e.event_type FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE m.organization_id=? AND m.outreach_strategy='FIXED_5'",(organization(),)).fetchall():events[r['message_id']].add(r['event_type'])
 def metrics(group):
  sent=[r for r in group if r['status']=='SENT'];out={'sent':len(sent)}
  for key,kind in [('delivered','DELIVERED'),('hard_bounced','BOUNCED_HARD'),('replied','REPLIED_VERIFIED'),('positive_reply','POSITIVE_REPLY'),('negative_reply','NEGATIVE_REPLY'),('unsubscribe','UNSUBSCRIBED')]:out[key]=sum(kind in events[r['id']] for r in sent)
  out['meeting']=len({r['prospect_id'] for r in sent if r['sales_state']=='MEETING'});out['positive_reply_rate']=round(out['positive_reply']/out['sent']*100,2) if sent else None;return out
 return {'ready':True,'organization':organization(),'qualification_mode':'CONTACTABLE_ONLY','analysis_enabled':False,'ai_copy_used':False,'pdf_asset_id':ASSET_ID,'pdf_version':VERSION,'contacted_recipients':c.execute('SELECT COUNT(*) FROM contacted_recipients WHERE organization_id=?',(organization(),)).fetchone()[0],'templates':[{'template_id':t,'template_version':VERSION,**metrics([r for r in rows if r['template_id']==t])} for t in TEMPLATES],'sources':[{'source':s,**metrics([r for r in rows if r['source_type']==s])} for s in ('OVERTURE','FIRECRAWL','FILE_IMPORT','GOOGLE_SHEETS')],'delivery_note':'SMTP acceptance is not proof of delivery; delivered requires a delivery event.'}
