"""Paginated permanent-prospect views; no second lead dataset or schema."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from app.automation.settings import effective_settings


def customer_summary(c, expected_organization=None):
    """Owned aggregate counts only; no internal runs, controls or provider flags."""
    from app.platform.context import current, organization
    from app.api.organization import require_role
    from app.mail.limits import MAX_PER_HOUR, MAX_PER_DAY
    org=organization(expected_organization)
    require_role(c,current().actor,org,('OWNER','ADMIN','MEMBER','VIEWER'))
    s=effective_settings(c)
    local=datetime.now(ZoneInfo(s.automation_timezone))
    start=local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat()
    today={
        'qualified':c.execute('SELECT COUNT(*) FROM master_lead_state m JOIN prospects p ON p.id=m.prospect_id AND p.organization_id=m.organization_id WHERE m.qualified_at>=? AND p.first_seen_at>=? AND m.organization_id=?',(start,start,org)).fetchone()[0],
        'sent':c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status='SENT' AND sent_at>=? AND organization_id=?",(start,org)).fetchone()[0],
        'replies':c.execute("SELECT COUNT(*) FROM activities WHERE event_type='REPLY_DETECTED' AND event_at>=? AND organization_id=?",(start,org)).fetchone()[0],
        'bounces':c.execute("SELECT COUNT(*) FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.event_type IN ('BOUNCED_HARD','BOUNCED_SOFT') AND e.occurred_at>=? AND m.organization_id=?",(start,org)).fetchone()[0],
        'queued':c.execute("SELECT COUNT(*) FROM automation_email_queue q JOIN master_lead_state m ON m.prospect_id=q.prospect_id JOIN prospects p ON p.id=m.prospect_id AND p.organization_id=m.organization_id WHERE m.organization_id=? AND q.status='QUEUED'",(org,)).fetchone()[0],
        'manual':c.execute("SELECT COUNT(*) FROM master_lead_state m JOIN prospects p ON p.id=m.prospect_id AND p.organization_id=m.organization_id WHERE m.contact_state='MANUAL_CONTACT_REQUIRED' AND m.organization_id=?",(org,)).fetchone()[0],
    }
    return {'today':today,
        'environment':{'daily_lead_target':s.daily_qualified_lead_target,'daily_email_target':s.daily_email_target,'hourly_limit':min(MAX_PER_HOUR,s.max_hour),'daily_limit':min(MAX_PER_DAY,s.max_day)},
        'contact_counts':[dict(r) for r in c.execute('SELECT m.contact_state,COUNT(*) AS count FROM master_lead_state m JOIN prospects p ON p.id=m.prospect_id AND p.organization_id=m.organization_id WHERE m.organization_id=? GROUP BY m.contact_state',(org,)).fetchall()],
        'queue':[dict(r) for r in c.execute('SELECT q.status,COUNT(*) AS count FROM automation_email_queue q JOIN master_lead_state m ON m.prospect_id=q.prospect_id JOIN prospects p ON p.id=m.prospect_id AND p.organization_id=m.organization_id WHERE m.organization_id=? GROUP BY q.status',(org,)).fetchall()]}

TABS={'all':'All Qualified','today':'New Today','ready':'Ready to Email','queued':'Email Queue','waiting':'Emailed / Waiting','replied':'Replied','manual':'Manual Contact Needed','connected':'Connected Manually','bounced':'Bounced','meeting':'Meetings','proposal':'Proposals','won':'Won','lost':'Lost','rejected':'Rejected / Not Interested','dnc':'Do Not Contact'}
BASE=""" FROM master_lead_state m JOIN prospects p ON p.id=m.prospect_id
 JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=p.id)
 LEFT JOIN business_intelligence i ON i.business_id=b.id
 LEFT JOIN opportunity_scores o ON o.business_id=b.id
 LEFT JOIN prospect_sales s ON s.prospect_id=p.id """
EMAIL="""EXISTS(SELECT 1 FROM businesses eb WHERE eb.prospect_id=p.id AND length(eb.public_email)>3 AND eb.public_email<>replace(eb.public_email,'@','') AND eb.public_email<>replace(eb.public_email,'.','') AND NOT EXISTS(SELECT 1 FROM email_address_suppressions es WHERE lower(es.address)=lower(eb.public_email) AND es.status IN ('INVALID','TEMPORARILY_UNUSABLE')) UNION SELECT 1 FROM contacts ec JOIN businesses eb ON eb.id=ec.business_id WHERE eb.prospect_id=p.id AND ec.contact_type='email' AND ec.is_valid=1 AND ec.is_public_business_contact=1 AND NOT EXISTS(SELECT 1 FROM email_address_suppressions es WHERE lower(es.address)=lower(ec.contact_value) AND es.status IN ('INVALID','TEMPORARILY_UNUSABLE')))"""
SOCIAL="(EXISTS(SELECT 1 FROM social_profiles sp WHERE sp.prospect_id=p.id) OR COALESCE(b.linkedin,b.instagram,b.facebook,b.x_url,'')<>'')"

def tab_conditions(c):
    local=datetime.now(ZoneInfo(effective_settings(c).automation_timezone))
    start=local.replace(hour=0,minute=0,second=0,microsecond=0)
    return {'all':('1=1',[]),'today':('p.first_seen_at>=? AND p.first_seen_at<?',[start.astimezone(timezone.utc).isoformat(),(start+timedelta(days=1)).astimezone(timezone.utc).isoformat()]),
            'ready':("m.contact_state='READY_TO_EMAIL'",[]),'queued':("m.contact_state='EMAIL_QUEUED'",[]),
            'waiting':("m.contact_state IN ('EMAILED','WAITING_REPLY')",[]),'replied':("m.contact_state='REPLIED'",[]),
            'manual':("m.contact_state='MANUAL_CONTACT_REQUIRED'",[]),'connected':("m.contact_state='CONNECTED_MANUALLY'",[]),
            'bounced':("(m.contact_state='EMAIL_BOUNCED' OR EXISTS(SELECT 1 FROM email_engagement_events e WHERE e.prospect_id=p.id AND e.event_type IN ('BOUNCED_HARD','BOUNCED_SOFT')))",[]),
            **{tab:('m.sales_state=?',[state]) for tab,state in [('meeting','MEETING'),('proposal','PROPOSAL'),('won','WON'),('lost','LOST')]},
            'rejected':("m.sales_state IN ('REJECTED','NOT_INTERESTED')",[]),'dnc':("(m.contact_state IN ('DO_NOT_CONTACT','UNSUBSCRIBED') OR p.lead_status='DO_NOT_CONTACT' OR s.suppressed_at IS NOT NULL)",[])}

def search(c,filters,tab='all',page=1,page_size=50,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    conditions=['m.organization_id=?'];args=[organization]
    for key,column in [('country','b.country'),('city','b.city'),('vertical','b.vertical'),('business_scale','i.business_scale'),('commercial_fit','i.commercial_fit'),('opportunity','o.primary_opportunity'),('contact_state','m.contact_state'),('sales_state','m.sales_state'),('assigned_to','p.assigned_to')]:
        if filters.get(key):conditions.append(column+'=?');args.append(filters[key])
    if filters.get('campaign_id'):
        conditions.append("EXISTS(SELECT 1 FROM businesses cb JOIN pipeline_runs cr ON cr.id=cb.run_id WHERE cb.prospect_id=p.id AND cr.campaign_id=?)");args.append(filters['campaign_id'])
    if filters.get('minimum_score'):
        conditions.append('(COALESCE(o.website_opportunity_score,0)>=? OR COALESCE(o.seo_opportunity_score,0)>=? OR COALESCE(o.security_opportunity_score,0)>=?)');args.extend([int(filters['minimum_score'])]*3)
    if filters.get('search'):
        value='%'+filters['search'].lower()+'%'
        conditions.append("(LOWER(b.name) LIKE ? OR LOWER(b.domain) LIKE ? OR LOWER(b.city) LIKE ? OR LOWER(b.country) LIKE ? OR b.phone LIKE ? OR EXISTS(SELECT 1 FROM businesses sb WHERE sb.prospect_id=p.id AND LOWER(sb.public_email) LIKE ?) OR EXISTS(SELECT 1 FROM prospect_notes n WHERE n.prospect_id=p.id AND LOWER(n.body) LIKE ? AND n.organization_id=?))")
        args.extend([value]*7+[organization])
    for key,operator in [('discovered_from','>='),('discovered_to','<=')]:
        if filters.get(key):conditions.append('p.first_seen_at'+operator+'?');args.append(filters[key])
    for key,sql in [('email_availability',EMAIL),('social_availability',SOCIAL)]:
        if filters.get(key) in ('yes','no'):conditions.append(('NOT ' if filters[key]=='no' else '')+sql)
    if filters.get('list_id'):
        conditions.append('EXISTS(SELECT 1 FROM lead_list_members lm WHERE lm.prospect_id=p.id AND lm.list_id=? AND lm.list_id IN (SELECT id FROM lead_lists WHERE organization_id=?))');args.extend([filters['list_id'],organization])
    where=' AND '.join(conditions) or '1=1'
    tabs=tab_conditions(c);aggregates=[];tab_args=[]
    for key,(clause,values) in tabs.items():
        aggregates.append('SUM(CASE WHEN '+clause+' THEN 1 ELSE 0 END) AS n_'+key);tab_args.extend(values)
    totals=c.execute('SELECT '+','.join(aggregates)+BASE+' WHERE '+where,[*tab_args,*args]).fetchone()
    counts={key:int(totals['n_'+key] or 0) for key in tabs}
    clause,values=tabs[tab]
    fields="""m.*,b.id AS business_id,b.name,b.city,b.country,b.vertical,b.domain,b.website,b.phone,b.public_email,b.linkedin,b.instagram,b.facebook,b.x_url,p.first_seen_at,p.last_seen_at,p.assigned_to,i.business_scale,i.commercial_fit,o.primary_opportunity,o.website_opportunity_score,o.seo_opportunity_score,o.security_opportunity_score,s.last_contact_at,(SELECT MIN(due_at) FROM followups f WHERE f.prospect_id=p.id AND f.status='OPEN') AS next_followup"""
    order={'newest':'m.qualified_at DESC,m.prospect_id','name':'LOWER(b.name),m.prospect_id','score':'(COALESCE(o.website_opportunity_score,0)+COALESCE(o.seo_opportunity_score,0)+COALESCE(o.security_opportunity_score,0)) DESC,m.prospect_id','last_touch':'s.last_contact_at DESC,m.prospect_id'}.get(filters.get('sort'),'m.qualified_at DESC,m.prospect_id')
    rows=[dict(r) for r in c.execute('SELECT '+fields+BASE+' WHERE '+where+' AND ('+clause+') ORDER BY '+order+' LIMIT ? OFFSET ?',[*args,*values,page_size,(page-1)*page_size]).fetchall()]
    if rows:
        profiles={}
        for r in c.execute('SELECT prospect_id,platform,profile_url FROM social_profiles WHERE prospect_id IN ('+','.join('?' for _ in rows)+')',[r['prospect_id'] for r in rows]).fetchall():profiles.setdefault(r['prospect_id'],[]).append(dict(r))
        for r in rows:r['social_profiles']=profiles.get(r['prospect_id'],[])
    return {'items':rows,'total':counts[tab],'page':page,'page_size':page_size,'counts':counts}
