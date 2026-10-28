"""Reviewed single-message sending, strong thread matching and bounded sync."""
import hashlib,hmac,json,re,uuid
from datetime import datetime,timezone,timedelta
from email.message import EmailMessage
from email.utils import make_msgid,formataddr,getaddresses,parsedate_to_datetime
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session,get_connection
from app.database.prospects import now,ProspectRepository
from app.mail.config import mail_settings
from app.mail import tracking,bounces
from app.mail.providers import provider,SendFailed,SendUncertain
from app.sales.service import activity,suppressed,ensure,schedule

ACCOUNT='hostinger-primary'
def address(value):
    if not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',value):raise HTTPException(422,'Use a valid email address without headers or display names.')
    return value.lower()
def header(value):
    if any(c in value for c in ('\r','\n','\x00')):raise HTTPException(422,'Email headers cannot contain newlines.')
    return value
def account(c,actor):
    s=mail_settings();stamp=now();address(s.from_address);header(s.from_name)
    c.execute("INSERT INTO email_accounts(id,user_id,provider,email_address,display_name,status,created_at,updated_at) VALUES(?,?,?,?,?,'CONNECTED',?,?) ON CONFLICT(id) DO NOTHING",(ACCOUNT,actor,'hostinger',s.from_address,s.from_name,stamp,stamp))
    return dict(c.execute('SELECT * FROM email_accounts WHERE id=?',(ACCOUNT,)).fetchone())
def recipients(c,pid):
    values=[]
    for row in c.execute('SELECT public_email FROM businesses WHERE prospect_id=? UNION SELECT x.contact_value FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id=? AND x.contact_type=\'email\' AND x.is_valid=1 AND x.is_public_business_contact=1',(pid,pid)).fetchall():
        try:email=address(row[0])
        except HTTPException:continue
        if email not in values:values.append(email)
    if tracking.available(c):
        blocked={r[0].lower() for r in c.execute("SELECT address FROM email_address_suppressions WHERE status IN ('INVALID','TEMPORARILY_UNUSABLE')").fetchall()}
        values=[v for v in values if v not in blocked]
    return values
def preview(c,pid,actor,body):
    s=mail_settings();acc=account(c,actor)
    if acc['status']!='CONNECTED':raise HTTPException(409,'The email account is disconnected.')
    if suppressed(c,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
    target=address(body['to_address'])
    if target not in recipients(c,pid):raise HTTPException(422,'Choose an email address stored as a public business contact.')
    subject=header(body['subject']).strip()
    if not subject or not body['body_text'].strip():raise HTTPException(422,'Write a subject and message before previewing.')
    if not s.sending_enabled:raise HTTPException(503,'Outbound email is disabled by the owner.')
    if s.mode not in ('test','production'):raise HTTPException(503,'Email send mode is not configured safely.')
    if (s.mode=='production') != s.live_approved:raise HTTPException(409,'Sending mode and manual live approval do not agree.')
    actual=address(s.test_recipient) if s.mode=='test' else target
    if body.get('thread_id') and not c.execute('SELECT 1 FROM email_threads WHERE id=? AND prospect_id=? AND account_id=?',(body['thread_id'],pid,ACCOUNT)).fetchone():raise HTTPException(404,'Conversation not found for this prospect.')
    if body.get('report_id') and not c.execute("SELECT 1 FROM client_reports WHERE id=? AND prospect_id=? AND status='READY'",(body['report_id'],pid)).fetchone():raise HTTPException(422,'Choose a ready PDF belonging to this prospect.')
    status=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
    if status=='NOT_INTERESTED' and not body.get('override_declined'):raise HTTPException(409,'This prospect declined. Explicitly confirm the manual override before continuing.')
    prefs=tracking.preferences(c)
    opens=bool(body.get('track_opens',True) and prefs['track_opens']);clicks=bool(body.get('track_clicks',True) and prefs['track_clicks'])
    if body.get('template_id') and not c.execute('SELECT 1 FROM email_templates WHERE id=? AND enabled=1',(body['template_id'],)).fetchone():raise HTTPException(422,'Choose an enabled stored template.')
    reviewed={k:body.get(k) for k in ('to_address','subject','body_text','report_id','thread_id','followup_days','override_declined')}
    reviewed.update(prospect_id=pid,effective_to=actual,from_address=s.from_address,mode=s.mode,track_opens=opens,track_clicks=clicks,template_id=body.get('template_id'),message_type=body.get('message_type','FIRST_CONTACT'))
    digest=json.dumps(reviewed,sort_keys=True,separators=(',',':')).encode();secret=get_settings().api_signing_secret or ('test-only-preview-secret' if get_settings().app_env=='test' else '')
    if not secret:raise HTTPException(503,'Email review signing is unavailable.')
    token=hmac.new(secret.encode(),digest,hashlib.sha256).hexdigest()
    return {'from_address':s.from_address,'from_name':s.from_name,'to_address':actual,'intended_to':target,'test_mode':s.mode=='test','subject':subject,'body_text':body['body_text'],'report_id':body.get('report_id'),'preview_token':token,'track_opens':opens,'track_clicks':clicks,'sending_enabled':s.sending_enabled}

def send(c,pid,actor,body):
    if body.get('confirmation')!='SEND':raise HTTPException(422,'Review the preview and confirm Send.')
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)');c.execute('SELECT pg_advisory_xact_lock(691944410)')
    result=preview(c,pid,actor,body)
    if not hmac.compare_digest(result['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Message or recipient changed. Review a new preview.')
    content_hash=hashlib.sha256(json.dumps({k:body.get(k) for k in ('to_address','subject','body_text','report_id','thread_id','followup_days','track_opens','track_clicks','template_id','message_type')},sort_keys=True).encode()).hexdigest()
    prior=c.execute('SELECT id,prospect_id,status,content_hash FROM email_messages WHERE idempotency_key=?',(body['idempotency_key'],)).fetchone()
    if prior:
        if prior['prospect_id']!=pid or prior['content_hash']!=content_hash:raise HTTPException(409,'This send key belongs to a different message.')
        return {'id':prior['id'],'status':prior['status'],'duplicate_prevented':True,'test_mode':result['test_mode']}
    s=mail_settings();hour=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat();day=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    hourly=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENDING','SENT') AND created_at>=?",(hour,)).fetchone()[0]
    daily=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENDING','SENT') AND created_at>=?",(day,)).fetchone()[0]
    if hourly>=s.max_hour or daily>=s.max_day:raise HTTPException(429,'The configured email sending limit has been reached.')
    message=EmailMessage();message['From']=formataddr((header(s.from_name),address(s.from_address)));message['To']=result['to_address'];message['Subject']=('[TEST] ' if result['test_mode'] else '')+result['subject'];message['Message-ID']=make_msgid(domain='planebyte.com');message['Date']=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    thread=body.get('thread_id');reply_to=None;references=[]
    if thread:
        previous=c.execute('SELECT provider_message_id,references_json FROM email_messages WHERE thread_id=? AND prospect_id=? ORDER BY created_at DESC LIMIT 1',(thread,pid)).fetchone()
        if previous:reply_to=previous['provider_message_id'];references=[*json.loads(previous['references_json']),reply_to][-20:];message['In-Reply-To']=header(reply_to);message['References']=' '.join(header(x) for x in references)
    else:
        thread=str(uuid.uuid4());c.execute("INSERT INTO email_threads VALUES(?,?,?,?,?,'OUTBOUND',?)",(thread,pid,ACCOUNT,result['subject'],now(),now()))
    text=result['body_text']
    if result['test_mode']:text='TEST MODE - redirected to a controlled mailbox. Intended public contact: '+result['intended_to']+'\n\n'+text
    message.set_content(text)
    if body.get('report_id'):
        from app.storage import artifact_storage
        report=c.execute('SELECT object_key FROM client_reports WHERE id=? AND prospect_id=?',(body['report_id'],pid)).fetchone()
        try:
            with artifact_storage().get(report[0]) as file:content=file.read(10_000_001)
        except Exception:raise HTTPException(503,'The selected PDF is temporarily unavailable.') from None
        if len(content)>10_000_000 or not content.startswith(b'%PDF-'):raise HTTPException(422,'The selected attachment is not a supported PDF.')
        message.add_attachment(content,maintype='application',subtype='pdf',filename='PlaneByte digital review.pdf')
    key=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,intended_to,subject,body_text,in_reply_to,references_json,report_id,created_at,idempotency_key,content_hash,test_mode) VALUES(?,?,?,?,?,'OUTBOUND','SENDING',?,?,?,?,?,?,?,?,?,?,?,?)",(key,pid,ACCOUNT,thread,str(message['Message-ID']),s.from_address,result['to_address'],result['intended_to'],result['subject'],result['body_text'],reply_to,json.dumps(references),body.get('report_id'),stamp,body['idempotency_key'],content_hash,int(result['test_mode'])))
    c.execute('UPDATE email_messages SET template_id=?,message_type=?,track_opens=?,track_clicks=? WHERE id=?',(body.get('template_id'),body.get('message_type','FIRST_CONTACT'),int(result['track_opens']),int(result['track_clicks']),key))
    plain,rich,optout=tracking.render_message(c,key,text,result['track_opens'],result['track_clicks'])
    # Keep the alternative inside multipart/mixed when the reviewed PDF is attached.
    target=message.get_payload(0) if message.get_content_type()=='multipart/mixed' else message
    target.set_content(plain);target.add_alternative(rich,subtype='html')
    message['List-Unsubscribe']='<'+optout+'>'
    message['List-Unsubscribe-Post']='List-Unsubscribe=One-Click'
    c.commit() # Reserve before SMTP. An uncertain result is never automatically resent.
    # Recheck suppression under the canonical lock immediately before SMTP.
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)')
    if suppressed(c,pid):c.execute("UPDATE email_messages SET status='FAILED',error_code='SUPPRESSED' WHERE id=?",(key,));c.commit();raise HTTPException(409,'This prospect is marked Do Not Contact.')
    # Repeat the reviewed recipient/account/report/config checks after reservation.
    try:
        final=preview(c,pid,actor,body)
        if not hmac.compare_digest(final['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Configuration changed. Review a fresh preview.')
        transport=provider()
        if not final['test_mode']:
            health=transport.health_check()
            if health.get('smtp')!='READY':raise HTTPException(503,'SMTP sending is not ready. Test the connection before sending.')
        # Refresh the reviewed checks after the potentially slow health connection.
        final=preview(c,pid,actor,body)
        if not hmac.compare_digest(final['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Review a fresh preview after the configuration change.')
        limit=mail_settings();stamp=datetime.now(timezone.utc)
        for span,maximum in [(timedelta(hours=1),limit.max_hour),(timedelta(days=1),limit.max_day)]:
            reserved=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENDING','SENT') AND created_at>=?",((stamp-span).isoformat(),)).fetchone()[0]
            if reserved>maximum:raise HTTPException(429,'The configured sending limit has been reached.')
        # The canonical lock remains held across this final check and SMTP.
        if suppressed(c,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
        transport.send_message(message)
    except HTTPException:
        c.execute("UPDATE email_messages SET status='FAILED',error_code='FINAL_SAFETY_CHECK' WHERE id=?",(key,));tracking.event(c,key,'SEND_FAILED',metadata={'reason':'FINAL_SAFETY_CHECK'});c.commit();raise
    except SendFailed:
        c.execute("UPDATE email_messages SET status='FAILED',error_code='SMTP_REJECTED_OR_CONNECTION' WHERE id=?",(key,));tracking.event(c,key,'SEND_FAILED',metadata={'reason':'SMTP_REJECTED_OR_CONNECTION'});c.commit();return {'id':key,'status':'FAILED','detail':'Email could not be sent. Review the account connection before trying a new message.'}
    except Exception:
        c.execute("UPDATE email_messages SET error_code='SMTP_RESULT_UNCERTAIN' WHERE id=?",(key,));c.commit();return {'id':key,'status':'SENDING','detail':'Send outcome is uncertain. Check the mailbox before sending again; automatic retries are blocked.'}
    c.execute("UPDATE email_messages SET status='SENT',sent_at=? WHERE id=?",(now(),key));c.execute("UPDATE email_threads SET last_message_at=?,last_direction='OUTBOUND' WHERE id=?",(now(),thread));ensure(c,pid);c.execute('UPDATE prospect_sales SET last_contact_at=? WHERE prospect_id=?',(now(),pid))
    tracking.event(c,key,'SMTP_ACCEPTED')
    activity(c,pid,actor,'EMAIL_SENT',{'message_id':key,'to':result['to_address'],'intended_to':result['intended_to'],'subject':result['subject'],'report_id':body.get('report_id'),'test_mode':result['test_mode']},'sent-'+key)
    current=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
    if current=='READY_TO_CONTACT':ProspectRepository(c).workflow(pid,actor,lead_status='CONTACTED')
    if body.get('followup_days'):schedule(c,pid,actor,(datetime.now(timezone.utc)+timedelta(days=body['followup_days'])).isoformat(),reason='Scheduled after reviewed email send')
    c.commit();return {'id':key,'status':'SENT','thread_id':thread,'test_mode':result['test_mode'],'provider_message_id':str(message['Message-ID'])}

def match_reply(c,incoming):
    refs=incoming.get('references',[])[:30]
    if not refs:return None
    rows=c.execute("SELECT id,prospect_id,thread_id,to_address,created_at,provider_message_id FROM email_messages WHERE account_id=? AND direction='OUTBOUND' AND status='SENT' AND provider_message_id IN ("+','.join('?' for _ in refs)+')',[ACCOUNT,*refs]).fetchall()
    if not rows or len({r['thread_id'] for r in rows})!=1:return None
    senders=[v.lower() for _,v in getaddresses([incoming['from']])];targets={v.lower() for _,v in getaddresses([incoming['to']])}
    if len(senders)!=1 or senders[0] not in {r['to_address'].lower() for r in rows} or mail_settings().from_address.lower() not in targets:return None
    try:
        date=parsedate_to_datetime(incoming['date']);date=date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        first=min(datetime.fromisoformat(r['created_at']) for r in rows)
        if date<first-timedelta(minutes=10) or date>datetime.now(timezone.utc)+timedelta(minutes=10):return None
    except (ValueError,TypeError):return None
    direct=incoming.get('in_reply_to','').strip()
    return next((r for r in rows if r['provider_message_id']==direct),max(rows,key=lambda r:r['created_at']))

def authenticated_reply(incoming):
    """Use the receiving provider's top Authentication-Results, not subject text."""
    value=incoming.get('authentication','').lower()
    authority=value.split(';',1)[0].strip().rstrip('.')
    if not any(authority==host or authority.endswith('.'+host) for host in ('hostinger.com','hostinger.io','titan.email','mailchannels.net')):return False
    senders=getaddresses([incoming.get('from','')])
    if len(senders)!=1 or '@' not in senders[0][1]:return False
    domain=senders[0][1].split('@',1)[1].lower()
    for clause in value.split(';'):
        if re.search(r'\bdmarc=pass\b',clause) and re.search(r'header\.from='+re.escape(domain)+r'(?:\s|$)',clause):return True
        if re.search(r'\bdkim=pass\b',clause) and re.search(r'header\.d='+re.escape(domain)+r'(?:\s|$)',clause):return True
    return False

def sync_mailbox(*, recheck=False):
    s=mail_settings()
    if not s.sync_enabled:return {'enabled':False}
    c=get_connection(session_bound=True);owner=str(uuid.uuid4())
    try:
        if get_settings().app_env=='production':
            active=c.execute("SELECT (SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') AND execution_name IS NOT NULL)+(SELECT COUNT(*) FROM client_reports WHERE status IN ('GENERATING','QUEUED') AND execution_name IS NOT NULL)").fetchone()[0]
            if active>=get_settings().max_active_scans:return {'deferred':True,'reason':'Heavy workers are at their configured limit.'}
        if getattr(c,'backend',None)=='postgres':
            if not c.execute('SELECT pg_try_advisory_lock(691944411)').fetchone()[0]:return {'busy':True}
        else:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT expires_at FROM email_sync_lock WHERE id=1').fetchone()
            if row and row[0]>now():return {'busy':True}
            c.execute('INSERT INTO email_sync_lock VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at',(owner,(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
        acc=account(c,get_settings().allowed_emails[0] if get_settings().allowed_emails else 'system')
        if acc['status']!='CONNECTED':return {'disconnected':True}
        known={r[0] for r in c.execute("SELECT provider_message_id FROM email_messages WHERE account_id=? AND status='SENT' AND direction='OUTBOUND' ORDER BY created_at DESC LIMIT 2000",(ACCOUNT,)).fetchall()}
        if not known:return {'received':0,'reason':'No tracked outbound messages yet.'}
        row=c.execute("SELECT * FROM email_sync_state WHERE account_id=? AND folder='INBOX'",(ACCOUNT,)).fetchone();cursor=dict(row) if row and not recheck else {};c.commit()
        messages,updated=provider().sync_messages(known,cursor);received=0
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)')
        for incoming in messages:
            if incoming.get('kind')=='dsn':
                bounces.process(c,incoming);continue
            if not re.fullmatch(r'<[^<>\s]{3,250}>',incoming.get('message_id','')):continue
            match=match_reply(c,incoming)
            if not match:continue
            pid=match['prospect_id'];thread=match['thread_id'];key=str(uuid.uuid4());stamp=now()
            changed=c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,references_json,created_at,received_at,test_mode) VALUES(?,?,?,?,?,'INBOUND','RECEIVED',?,?,?,?,?,?,?,?) ON CONFLICT(account_id,provider_message_id) DO NOTHING",(key,pid,ACCOUNT,thread,incoming['message_id'],getaddresses([incoming['from']])[0][1],s.from_address,incoming['subject'],incoming['body_text'],json.dumps(incoming['references']),stamp,stamp,int(s.mode=='test'))).rowcount
            if not changed:
                existing=c.execute('SELECT id,prospect_id,thread_id FROM email_messages WHERE account_id=? AND provider_message_id=?',(ACCOUNT,incoming['message_id'])).fetchone()
                if existing['prospect_id']!=pid or existing['thread_id']!=thread:continue
                key=existing['id']
                if c.execute('SELECT 1 FROM activities WHERE dedup_key=?',('reply-'+key,)).fetchone():continue
            verified=authenticated_reply(incoming)
            if verified and tracking.preferences(c)['track_replies']:tracking.event(c,match['id'],'REPLIED_VERIFIED',dedup='verified-'+key,metadata={'inbound_message_id':key})
            if not changed and not verified:continue
            received+=int(bool(changed));c.execute("UPDATE email_threads SET last_message_at=?,last_direction='INBOUND' WHERE id=?",(stamp,thread));ensure(c,pid)
            if verified:c.execute('UPDATE prospect_sales SET unread_replies=unread_replies+1 WHERE prospect_id=?',(pid,))
            activity(c,pid,'system','EMAIL_RECEIVED',{'message_id':key,'reply_verified':verified,'test_mode':s.mode=='test'},'received-'+key)
            if verified:
                c.execute('UPDATE activities SET metadata_json=? WHERE dedup_key=?',(json.dumps({'message_id':key,'reply_verified':True,'test_mode':s.mode=='test'}),'received-'+key))
            if verified:activity(c,pid,'system','REPLY_DETECTED',{'message_id':key,'match':'Message-ID references + peer address + mailbox + time window + aligned provider authentication','test_mode':s.mode=='test'},'reply-'+key)
            current=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
            if verified and current in ('CONTACTED','FOLLOW_UP') and not suppressed(c,pid):ProspectRepository(c).workflow(pid,'system',lead_status='REPLIED')
        c.execute("INSERT INTO email_sync_state(account_id,folder,uidvalidity,last_uid) VALUES(?,'INBOX',?,?) ON CONFLICT(account_id,folder) DO UPDATE SET uidvalidity=excluded.uidvalidity,last_uid=excluded.last_uid",(ACCOUNT,updated.get('uidvalidity',''),max(updated.get('last_uid',0), row['last_uid'] if row and row['uidvalidity']==updated.get('uidvalidity') else 0)))
        c.execute('UPDATE email_accounts SET last_sync_at=?,updated_at=? WHERE id=?',(now(),now(),ACCOUNT));c.commit();return {'received':received,'checked':len(messages),'last_sync_at':now()}
    finally:
        if getattr(c,'backend',None)!='postgres':
            c.execute('DELETE FROM email_sync_lock WHERE owner=?',(owner,));c.commit()
        c.close()
