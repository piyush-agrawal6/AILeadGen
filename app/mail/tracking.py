"""First-party, privacy-limited signals attached to the existing activity timeline."""
import hashlib,html,ipaddress,json,re,secrets,time,uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,urlunsplit
from fastapi import HTTPException
from app.database.prospects import now
from app.mail.config import mail_settings
from app.sales.service import activity,ensure

EVENT_LABELS={'SMTP_ACCEPTED':'Sent','SEND_FAILED':'Send failed','BOUNCED_SOFT':'Soft bounce','BOUNCED_HARD':'Hard bounce','OPEN_SIGNAL':'Open signal','CLICK_SIGNAL':'Click signal','REPLIED_VERIFIED':'Verified reply','UNSUBSCRIBED':'Unsubscribed','SUPPRESSED':'Suppressed','DRAFT':'Draft','SENDING':'Sending'}
ACTIVITY_TYPES={'SMTP_ACCEPTED':'EMAIL_SMTP_ACCEPTED','SEND_FAILED':'EMAIL_SEND_FAILED','BOUNCED_SOFT':'EMAIL_BOUNCED_SOFT','BOUNCED_HARD':'EMAIL_BOUNCED_HARD','OPEN_SIGNAL':'EMAIL_OPEN_SIGNAL','CLICK_SIGNAL':'EMAIL_CLICK_SIGNAL','REPLIED_VERIFIED':'EMAIL_REPLY_VERIFIED','UNSUBSCRIBED':'EMAIL_UNSUBSCRIBED','SUPPRESSED':'EMAIL_SUPPRESSED'}
TOKEN_RE=re.compile(r'^[A-Za-z0-9_-]{43}$')

def available(c):
    return (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=8

def preferences(c):
    return {k:bool(v) for k,v in dict(c.execute('SELECT track_opens,track_clicks,track_replies,track_bounces FROM email_tracking_preferences WHERE id=1').fetchone()).items()}

def allowed_url(value):
    """No fetch is performed. Only stored public HTTPS/HTTP destinations redirect."""
    if not isinstance(value,str) or len(value)>2048 or any(ord(x)<33 for x in value) or '\\' in value:return None
    try:
        parsed=urlsplit(value);host=(parsed.hostname or '').rstrip('.').lower()
        if parsed.scheme not in ('http','https') or parsed.username or parsed.password or not host or parsed.port not in (None,80,443):return None
        if host in ('localhost','localhost.localdomain') or host.endswith(('.local','.localhost','.internal','.test','.example','.invalid')) or '.' not in host:return None
        try:
            if not ipaddress.ip_address(host).is_global:return None
        except ValueError:
            if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',host):return None
            # Reject legacy numeric IP forms and decimal/octal/hex host encodings.
            if all(re.fullmatch(r'(?:0x[0-9a-f]+|[0-9]+)',part) for part in host.split('.')):return None
        return urlunsplit(parsed)
    except (ValueError,UnicodeError):return None

def tracking_base():
    raw=mail_settings().tracking_base_url.rstrip('/')
    parsed=urlsplit(raw)
    if not allowed_url(raw) or parsed.scheme!='https' or parsed.query or parsed.fragment:raise HTTPException(503,'Tracking requires a configured public HTTPS base URL.')
    return raw

def issue_token(c,message_id,action,destination=None):
    token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
    c.execute('INSERT INTO email_tracking_tokens VALUES(?,?,?,?,?,?)',(digest,message_id,action,destination,now(),(datetime.now(timezone.utc)+timedelta(days=365)).isoformat()))
    return tracking_base()+'/'+action+'/'+token+('.gif' if action=='o' else '')

def lookup(c,token,action):
    if not TOKEN_RE.fullmatch(token):return None
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=c.execute("SELECT t.*,m.prospect_id,m.thread_id,m.test_mode,m.status FROM email_tracking_tokens t JOIN email_messages m ON m.id=t.message_id WHERE token_hash=? AND action=? AND expires_at>? AND m.status='SENT'",(digest,action,now())).fetchone()
    return dict(row) if row else None

def classify(method,agent,fetch_user=''):
    ua=agent.lower()[:1024]
    automated=method=='HEAD' or any(x in ua for x in ('bot','crawler','spider','scanner','proofpoint','mimecast','safelinks','barracuda','googleimageproxy','google-image-proxy','yahoo','outlook-ios','applemail','mailprivacy','preview','curl','python-requests','headless'))
    if automated:return 'AUTOMATED','scanner_or_proxy',True
    if method=='GET' and fetch_user=='?1' and any(x in ua for x in ('mozilla','chrome','safari','firefox')):return 'LIKELY_HUMAN','interactive_browser',False
    return 'UNKNOWN','mail_client_or_unknown',False

def event(c,message_id,kind,*,dedup=None,token_id=None,quality='UNKNOWN',category=None,bot=False,metadata=None,occurred_at=None):
    row=c.execute('SELECT id,thread_id,prospect_id,test_mode FROM email_messages WHERE id=?',(message_id,)).fetchone()
    if not row:return False
    key=dedup or kind+':'+message_id;stamp=occurred_at or now();eid=str(uuid.uuid4())
    inserted=c.execute('INSERT INTO email_engagement_events(id,message_id,thread_id,prospect_id,event_type,occurred_at,last_at,token_id,url_id,user_agent_category,signal_quality,suspected_bot,metadata_json,created_at,dedup_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',(eid,message_id,row['thread_id'],row['prospect_id'],kind,stamp,stamp,token_id,token_id if kind=='CLICK_SIGNAL' else None,category,quality,int(bot),json.dumps(metadata or {}),stamp,key)).rowcount
    if not inserted:
        c.execute('UPDATE email_engagement_events SET last_at=?,request_count=request_count+1 WHERE dedup_key=?',(stamp,key));return False
    activity(c,row['prospect_id'],'system',ACTIVITY_TYPES.get(kind,'EMAIL_'+kind),{'message_id':message_id,'test_mode':bool(row['test_mode']),'signal_quality':quality,'suspected_bot':bot,**(metadata or {})},'engagement-'+key,event_at=stamp)
    return True

def render_message(c,message_id,text,opens,clicks):
    base=tracking_base();parts=[];plain=[];offset=0
    for match in re.finditer(r'https?://[^\s<>"\x27]+',text):
        original=match.group().rstrip('.,);!?');end=match.start()+len(original);destination=allowed_url(original)
        parts.append(html.escape(text[offset:match.start()]));plain.append(text[offset:match.start()])
        # Signed/private report URLs remain untouched. Existing attachments stay private.
        protected=any(x in original.lower() for x in ('x-amz-','signature=','/api/client-reports/','/download','/unsubscribe'))
        eligible=destination and not original.startswith(base) and not protected
        link=issue_token(c,message_id,'c',destination) if clicks and eligible else destination
        if link:parts.append('<a href="'+html.escape(link,quote=True)+'">'+html.escape(original)+'</a>');plain.append(link)
        else:parts.append(html.escape(original));plain.append(original)
        offset=end
    parts.append(html.escape(text[offset:]));plain.append(text[offset:])
    unsubscribe=issue_token(c,message_id,'u')
    footer='\n\nStop receiving emails: '+unsubscribe
    body='<div style="font-family:Arial,sans-serif;white-space:pre-wrap">'+''.join(parts)+'</div><p style="font:12px Arial;color:#666"><a href="'+html.escape(unsubscribe,quote=True)+'">Stop receiving emails</a></p>'
    if opens:body+='<img alt="" width="1" height="1" src="'+issue_token(c,message_id,'o')+'">'
    return ''.join(plain)+footer,body,unsubscribe

def rate_allowed(c,token,action):
    # Global, durable bounded endpoint budget; no raw IP or user agent is persisted.
    minute=int(time.time())//60
    keys=[('global:'+str(minute),600),('token:'+hashlib.sha256(token.encode()).hexdigest()+':'+str(minute),30)]
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944412)')
    c.execute('DELETE FROM email_tracking_rate_limits WHERE expires_at<?',(int(time.time()),))
    for key,limit in keys:
        c.execute('INSERT INTO email_tracking_rate_limits VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET requests=email_tracking_rate_limits.requests+1',(key,int(time.time())+120))
        if c.execute('SELECT requests FROM email_tracking_rate_limits WHERE bucket=?',(key,)).fetchone()[0]>limit:return False
    return True

def public_signal(c,row,method,agent,fetch_user=''):
    quality,category,bot=classify(method,agent,fetch_user)
    # First/last/request count retained per token and quality; UI counts distinct messages/links.
    event(c,row['message_id'],'OPEN_SIGNAL' if row['action']=='o' else 'CLICK_SIGNAL',dedup=row['action']+':'+row['token_hash']+':'+quality,token_id=row['token_hash'],quality=quality,category=category,bot=bot,metadata={'destination_host':urlsplit(row['destination']).hostname} if row['destination'] else {})

def unsubscribe(c,row):
    if row['test_mode']:
        event(c,row['message_id'],'UNSUBSCRIBED',metadata={'simulation':True,'source':'RECIPIENT_UNSUBSCRIBE','suppression_applied':False});return
    from app.database.prospects import ProspectRepository
    ensure(c,row['prospect_id']);ProspectRepository(c).workflow(row['prospect_id'],'system',lead_status='DO_NOT_CONTACT')
    c.execute("UPDATE prospect_sales SET suppression_source='RECIPIENT_UNSUBSCRIBE' WHERE prospect_id=?",(row['prospect_id'],))
    event(c,row['message_id'],'UNSUBSCRIBED',metadata={'source':'RECIPIENT_UNSUBSCRIBE','suppression_applied':True})

def message_summary(c,message_id):
    rows=[dict(r) for r in c.execute('SELECT event_type,occurred_at,last_at,signal_quality,suspected_bot,metadata_json FROM email_engagement_events WHERE message_id=? ORDER BY occurred_at',(message_id,)).fetchall()]
    kinds={r['event_type'] for r in rows};priority=['UNSUBSCRIBED','SUPPRESSED','BOUNCED_HARD','REPLIED_VERIFIED','BOUNCED_SOFT','CLICK_SIGNAL','OPEN_SIGNAL','SEND_FAILED','SMTP_ACCEPTED']
    strongest=next((k for k in priority if k in kinds and (k not in ('OPEN_SIGNAL','CLICK_SIGNAL') or any(r['event_type']==k and not r['suspected_bot'] for r in rows))),None)
    return {'label':EVENT_LABELS.get(strongest,'—'),'event_type':strongest,'events':[{**r,'metadata':json.loads(r.pop('metadata_json'))} for r in rows], 'first_open_signal_at':min((r['occurred_at'] for r in rows if r['event_type']=='OPEN_SIGNAL'),default=None),'last_open_signal_at':max((r['last_at'] for r in rows if r['event_type']=='OPEN_SIGNAL'),default=None),'open_signal_count':int('OPEN_SIGNAL' in kinds)}

def lead_summary(c,pid):
    rows=[dict(r) for r in c.execute('SELECT event_type,COUNT(DISTINCT message_id) AS n,MAX(last_at) AS last_at FROM email_engagement_events WHERE prospect_id=? AND suspected_bot=0 GROUP BY event_type',(pid,)).fetchall()]
    counts={r['event_type']:r['n'] for r in rows};last=max((r['last_at'] for r in rows),default=None)
    human=c.execute("SELECT 1 FROM email_engagement_events WHERE prospect_id=? AND event_type='CLICK_SIGNAL' AND signal_quality='LIKELY_HUMAN' LIMIT 1",(pid,)).fetchone()
    level='HIGH' if counts.get('REPLIED_VERIFIED') else 'MEDIUM' if human else 'LOW' if counts.get('OPEN_SIGNAL') else 'NONE'
    priority=['UNSUBSCRIBED','SUPPRESSED','REPLIED_VERIFIED','BOUNCED_HARD','BOUNCED_SOFT','CLICK_SIGNAL','OPEN_SIGNAL','SEND_FAILED','SMTP_ACCEPTED']
    strongest=next((k for k in priority if counts.get(k)),None)
    mode_counts={int(r['test_mode']):r['n'] for r in c.execute("SELECT test_mode,COUNT(*) AS n FROM email_messages WHERE prospect_id=? AND direction='OUTBOUND' AND status='SENT' GROUP BY test_mode",(pid,)).fetchall()}
    test_only=bool(mode_counts.get(1) and not mode_counts.get(0))
    return {'test_only':test_only,'test_messages_sent':mode_counts.get(1,0),'messages_sent':c.execute("SELECT COUNT(*) FROM email_messages WHERE prospect_id=? AND direction='OUTBOUND' AND status='SENT'",(pid,)).fetchone()[0], 'open_signals':counts.get('OPEN_SIGNAL',0),'click_signals':counts.get('CLICK_SIGNAL',0),'verified_replies':counts.get('REPLIED_VERIFIED',0),'last_engagement_at':last,'level':level,'label':EVENT_LABELS.get(strongest,'-')+(' (Test)' if test_only else '')}


def backfill(c):
    """Add facts from accepted Phase 4 records; never invent historical signals."""
    for row in c.execute("SELECT id,status,sent_at,created_at FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENT','FAILED')").fetchall():
        event(c,row['id'],'SMTP_ACCEPTED' if row['status']=='SENT' else 'SEND_FAILED',occurred_at=row['sent_at'] or row['created_at'])
    for row in c.execute("SELECT metadata_json,prospect_id,event_at FROM activities WHERE event_type='REPLY_DETECTED'").fetchall():
        inbound_id=json.loads(row['metadata_json']).get('message_id')
        incoming=c.execute('SELECT thread_id,references_json FROM email_messages WHERE id=?',(inbound_id,)).fetchone()
        if not incoming:continue
        refs=json.loads(incoming['references_json'])
        for ref in refs:
            sent=c.execute("SELECT id FROM email_messages WHERE thread_id=? AND direction='OUTBOUND' AND provider_message_id=?",(incoming['thread_id'],ref)).fetchone()
            if sent:event(c,sent['id'],'REPLIED_VERIFIED',dedup='verified-'+inbound_id,metadata={'inbound_message_id':inbound_id,'backfilled':True},occurred_at=row['event_at']);break
