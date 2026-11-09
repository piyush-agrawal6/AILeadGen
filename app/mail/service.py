from app.mail.limits import MAX_PER_HOUR,MAX_PER_DAY,MIN_SPACING_SECONDS
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

ACCOUNT=mail_settings().provider+'-primary'
def address(value):
    if not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',value):raise HTTPException(422,'Use a valid email address without headers or display names.')
    return value.lower()
def header(value):
    if any(c in value for c in ('\r','\n','\x00')):raise HTTPException(422,'Email headers cannot contain newlines.')
    return value
def account(c,actor,account_id=None):
    from app.platform.context import organization
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if organization()!=PLANEBYTE_ORGANIZATION_ID or (account_id and account_id!=ACCOUNT):
        from app.mail.customer import owned_account
        return owned_account(c,actor,account_id)
    from app.platform.context import require_internal_mailbox
    context=require_internal_mailbox()
    s=mail_settings();stamp=now();address(s.from_address);header(s.from_name)
    prior=c.execute('SELECT organization_id FROM email_accounts WHERE id=?',(ACCOUNT,)).fetchone()
    if prior and prior[0]!=context.organization_id:raise HTTPException(409,'The internal mailbox ownership requires review.')
    c.execute("INSERT INTO email_accounts(id,user_id,provider,email_address,display_name,status,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,'CONNECTED',?,?,?) ON CONFLICT(id) DO NOTHING",(ACCOUNT,actor,s.provider,s.from_address,s.from_name,stamp,stamp,context.organization_id))
    return dict(c.execute('SELECT * FROM email_accounts WHERE id=? AND organization_id=?',(ACCOUNT,context.organization_id)).fetchone())

def settings_for(c,acc=None):
    from app.platform.context import current
    acc=acc or account(c,current().actor)
    if acc['provider']=='gmail_oauth':
        from app.mail.customer import settings
        return settings(c,acc)
    from app.automation.settings import effective_settings
    return effective_settings(c,mail_settings())

def transport_for(c,acc):
    if acc['provider']=='gmail_oauth':
        from app.mail.customer import GmailProvider
        return GmailProvider(c,acc)
    from app.platform.context import require_internal_mailbox
    require_internal_mailbox()
    return provider()
def recipients(c,pid):
    from app.platform.context import organization
    org=organization()
    if not c.execute('SELECT 1 FROM prospects WHERE id=? AND organization_id=?',(pid,org)).fetchone():raise HTTPException(404,'Prospect not found in this workspace.')
    values=[]
    for row in c.execute('SELECT public_email FROM businesses WHERE prospect_id=? UNION SELECT x.contact_value FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id=? AND x.contact_type=\'email\' AND x.is_valid=1 AND x.is_public_business_contact=1',(pid,pid)).fetchall():
        try:email=address(row[0])
        except HTTPException:continue
        if email not in values:values.append(email)
    if tracking.available(c):
        blocked={r[0].lower() for r in c.execute("SELECT address FROM email_address_suppressions WHERE organization_id=? AND status IN ('INVALID','TEMPORARILY_UNUSABLE')",(org,)).fetchall()}
        values=[v for v in values if v not in blocked]
    if (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=40:
        blocked={r[0].lower() for r in c.execute("SELECT address FROM customer_mail_suppressions WHERE organization_id=? AND status IN ('INVALID','TEMPORARILY_UNUSABLE')",(org,)).fetchall()}
        values=[v for v in values if v not in blocked]
    return values
def preview(c,pid,actor,body,*,allow_disabled=False):
    from app.platform.context import current
    context=current()
    if not c.execute('SELECT 1 FROM prospects WHERE id=? AND organization_id=?',(pid,context.organization_id)).fetchone():raise HTTPException(404,'Prospect not found in this workspace.')
    if body.get('campaign_id') and not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(body['campaign_id'],context.organization_id)).fetchone():raise HTTPException(404,'Campaign not found in this workspace.')
    if body.get('outreach_strategy')=='FIXED_5' or body.get('experiment_member_id'):
        raise HTTPException(409,'Internal experiment outreach is archived. Use a workspace-owned template.')
    acc=account(c,actor,body.get('account_id'));s=settings_for(c,acc)
    if acc['status']!='CONNECTED' or acc.get('connection_status','CONNECTED')!='CONNECTED':raise HTTPException(409,'The email account is disconnected.')
    if acc['provider']=='gmail_oauth' and body.get('campaign_id'):
        from app.mail.customer import validate_campaign
        validate_campaign(c,body['campaign_id'],acc['id'])
    if suppressed(c,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
    target=address(body['to_address'])
    from app.mail.contacted import ensure_new
    ensure_new(c,target,idempotency_key=body.get('idempotency_key'))
    if target not in recipients(c,pid):raise HTTPException(422,'Choose an email address stored as a public business contact.')
    subject=header(body['subject']).strip()
    if not subject or not body['body_text'].strip():raise HTTPException(422,'Write a subject and message before previewing.')
    if not s.sending_enabled and not allow_disabled:raise HTTPException(503,'Outbound email is disabled by the owner.')
    if s.mode not in ('test','production'):raise HTTPException(503,'Email send mode is not configured safely.')
    if (s.mode=='production') != s.live_approved:raise HTTPException(409,'Sending mode and manual live approval do not agree.')
    if acc['provider']=='gmail_oauth' and s.mode=='production' and get_settings().app_env!='production' and not allow_disabled:raise HTTPException(503,'Customer live sending is unavailable in this environment.')
    actual=address(s.test_recipient) if s.mode=='test' and (s.test_recipient or not allow_disabled) else target
    if body.get('thread_id') and not c.execute('SELECT 1 FROM email_threads WHERE id=? AND prospect_id=? AND account_id=? AND organization_id=?',(body['thread_id'],pid,acc['id'],context.organization_id)).fetchone():raise HTTPException(404,'Conversation not found for this prospect.')
    if body.get('report_id') and body.get('message_type','FIRST_CONTACT')=='FIRST_CONTACT':raise HTTPException(409,'Historical audit PDFs are not part of Lead Engine outreach. Review a message without an assessment attachment.')
    if body.get('report_id') and not c.execute("SELECT 1 FROM client_reports WHERE id=? AND prospect_id=? AND status='READY'",(body['report_id'],pid)).fetchone():raise HTTPException(422,'Choose a ready PDF belonging to this prospect.')
    status=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
    if status=='NOT_INTERESTED' and not body.get('override_declined'):raise HTTPException(409,'This prospect declined. Explicitly confirm the manual override before continuing.')
    prefs=tracking.preferences(c)
    opens=bool(s.tracking_enabled and body.get('track_opens',True) and prefs['track_opens']);clicks=bool(s.tracking_enabled and body.get('track_clicks',True) and prefs['track_clicks'])
    if body.get('template_id') and not c.execute('SELECT 1 FROM email_templates WHERE id=? AND enabled=1 AND organization_id=?',(body['template_id'],context.organization_id)).fetchone():raise HTTPException(422,'Choose an enabled stored template.')
    reviewed={k:body.get(k) for k in ('to_address','subject','body_text','report_id','thread_id','followup_days','override_declined','preview_nonce','campaign_id','pitch_types','experiment_member_id','catalog_snapshot','outreach_strategy','template_version','pdf_asset_id','pdf_version')}
    reviewed.update(prospect_id=pid,effective_to=actual,from_address=s.from_address,mode=s.mode,track_opens=opens,track_clicks=clicks,template_id=body.get('template_id'),message_type=body.get('message_type','FIRST_CONTACT'))
    if acc['provider']=='gmail_oauth':
        from app.mail.customer import policy
        reviewed.update(account_id=acc['id'],mailbox_revision=acc['mailbox_revision'],policy_revision=policy(c)['revision'])
    digest=json.dumps(reviewed,sort_keys=True,separators=(',',':')).encode();secret=get_settings().api_signing_secret or ('test-only-preview-secret' if get_settings().app_env=='test' else '')
    if not secret:raise HTTPException(503,'Email review signing is unavailable.')
    token=hmac.new(secret.encode(),digest,hashlib.sha256).hexdigest()
    display_text=body['body_text']
    if s.mode=='test':display_text='TEST MODE - redirected to a controlled mailbox. Intended public contact: '+target+'\n\n'+display_text
    seed=render_seed(token) if body.get('preview_nonce') else None
    plain,rich,optout=tracking.render_message(c,'preview',display_text,opens,clicks,seed=seed,persist=False)
    from app.mail.quality import issues
    problems=issues(c,pid,body,settings=s) if s.mode=='production' else []
    result={'from_address':s.from_address,'from_name':s.from_name,'to_address':actual,'intended_to':target,'test_mode':s.mode=='test','subject':subject,'body_text':body['body_text'],'report_id':body.get('report_id'),'preview_token':token,'track_opens':opens,'track_clicks':clicks,'sending_enabled':s.sending_enabled}
    result.update(rendered_subject=('[TEST] ' if s.mode=='test' else '')+subject,rendered_text=plain,rendered_html=rich,quality_issues=problems,preview_nonce=body.get('preview_nonce'))
    if acc['provider']=='gmail_oauth':result.update(account_id=acc['id'],mailbox_revision=acc['mailbox_revision'])
    if body.get('outreach_strategy')=='FIXED_5':
        from app.outreach.fixed import asset
        a=asset(c,body.get('pdf_version'));result['pdf_attachment']={k:a[k] for k in ('id','version','filename','size_bytes')};result['pdf_attachment']['url']='/api/email/company-pdf/'+a['version']
    return result

def render_seed(token):
    secret=get_settings().api_signing_secret or 'test-only-preview-secret'
    return hmac.new(secret.encode(),('mime:'+token).encode(),hashlib.sha256).hexdigest()


def send(c,pid,actor,body,*,controlled_envelope_to=None,controlled_authorization=None):
    from app.platform.context import organization
    acc=account(c,actor,body.get('account_id'))
    if acc['provider']=='gmail_oauth' and controlled_envelope_to is not None:raise HTTPException(403,'Internal mailbox redirects cannot authorize customer sends.')
    redirected=controlled_envelope_to is not None
    if redirected:
        controlled_envelope_to=address(controlled_envelope_to)
        if not controlled_authorization or len(controlled_authorization)>200:raise HTTPException(422,'Owner-controlled redirect authorization is required.')
    elif controlled_authorization:raise HTTPException(422,'Controlled recipient is required.')
    if body.get('confirmation')!='SEND':raise HTTPException(422,'Review the preview and confirm Send.')
    if acc['provider']=='gmail_oauth' and body.get('workflow_run_id'):
        from app.mail.customer import validate_execution
        validate_execution(c,body['workflow_run_id'],acc['id'])
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)');c.execute('SELECT pg_advisory_xact_lock(691944410)')
    result=preview(c,pid,actor,body)
    if not hmac.compare_digest(result['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Message or recipient changed. Review a new preview.')
    hashed={k:body.get(k) for k in ('to_address','subject','body_text','report_id','thread_id','followup_days','track_opens','track_clicks','template_id','message_type','campaign_id','pitch_types','experiment_member_id','catalog_snapshot','outreach_strategy','template_version','pdf_asset_id','pdf_version','account_id')}
    if redirected:hashed.update(controlled_envelope_to=controlled_envelope_to,controlled_authorization=controlled_authorization)
    content_hash=hashlib.sha256(json.dumps(hashed,sort_keys=True).encode()).hexdigest()
    prior=c.execute('SELECT id,prospect_id,status,content_hash,organization_id,account_id FROM email_messages WHERE idempotency_key=?',(body['idempotency_key'],)).fetchone()
    if prior:
        if prior['organization_id']!=organization() or prior['account_id']!=acc['id']:raise HTTPException(409,'This send key is unavailable for this workspace mailbox.')
        if prior['prospect_id']!=pid or prior['content_hash']!=content_hash:raise HTTPException(409,'This send key belongs to a different message.')
        return {'id':prior['id'],'status':prior['status'],'duplicate_prevented':True,'test_mode':result['test_mode']}
    if acc['provider']=='gmail_oauth':
        from app.mail.customer import reserve_spacing
        reserve_spacing(c,acc)
    s=settings_for(c,acc);hour=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat();day=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    if s.mode=='production' and not redirected:
        from app.workflows.controls import require_unpaused
        require_unpaused(c,'email')
    from app.mail.contacted import usage
    hourly=usage(c,hour)
    daily=usage(c,day)
    if hourly>=min(MAX_PER_HOUR,s.max_hour) or daily>=min(MAX_PER_DAY,s.max_day):raise HTTPException(429,'The configured email sending limit has been reached.')
    if redirected:result={**result,'intended_to':address(body['to_address']),'to_address':controlled_envelope_to,'test_mode':True}
    if s.mode=='production' and body.get('message_type','FIRST_CONTACT')=='FIRST_CONTACT':
        from app.mail.quality import issues
        problems=issues(c,pid,body,settings=s)
        if problems:raise HTTPException(422,'Needs Review: '+' '.join(problems))
    if body.get('experiment_member_id') and not redirected:
        from app.experiments.runtime import send_gate
        send_gate(c,body)
    message=EmailMessage();message['From']=formataddr((header(s.from_name),address(s.from_address)));message['To']=result['to_address'];message['Subject']=('[TEST] ' if result['test_mode'] and not redirected else '')+result['subject'];message['Message-ID']=make_msgid(domain=s.from_address.rsplit('@',1)[1]);message['Date']=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    thread=body.get('thread_id');reply_to=None;references=[]
    if thread:
        previous=c.execute('SELECT provider_message_id,references_json FROM email_messages WHERE thread_id=? AND prospect_id=? ORDER BY created_at DESC LIMIT 1',(thread,pid)).fetchone()
        if previous:reply_to=previous['provider_message_id'];references=[*json.loads(previous['references_json']),reply_to][-20:];message['In-Reply-To']=header(reply_to);message['References']=' '.join(header(x) for x in references)
    else:
        thread=str(uuid.uuid4());c.execute("INSERT INTO email_threads(id,prospect_id,account_id,subject,last_message_at,last_direction,created_at,organization_id) VALUES(?,?,?,?,?,'OUTBOUND',?,?)",(thread,pid,acc['id'],result['subject'],now(),now(),organization()))
    text=result['body_text']
    if result['test_mode'] and not redirected:text='TEST MODE - redirected to a controlled mailbox. Intended public contact: '+result['intended_to']+'\n\n'+text
    message.set_content(text)
    if body.get('outreach_strategy')=='FIXED_5':
        from app.outreach.fixed import attachment
        content,filename=attachment(c,body);message.add_attachment(content,maintype='application',subtype='pdf',filename=filename)
    if body.get('report_id'):
        from app.storage import artifact_storage
        report=c.execute('SELECT object_key,snapshot_json FROM client_reports WHERE id=? AND prospect_id=?',(body['report_id'],pid)).fetchone()
        try:
            with artifact_storage().get(report[0]) as file:content=file.read(10_000_001)
        except Exception:raise HTTPException(503,'The selected PDF is temporarily unavailable.') from None
        if len(content)>10_000_000 or not content.startswith(b'%PDF-'):raise HTTPException(422,'The selected attachment is not a supported PDF.')
        if s.mode=='production':
            from app.mail.quality import validate_pdf
            validate_pdf(content,report_type=json.loads(report['snapshot_json']).get('report_type','FULL_AUDIT'))
        message.add_attachment(content,maintype='application',subtype='pdf',filename='PlaneByte Digital Opportunity Brief.pdf' if json.loads(report['snapshot_json']).get('report_type')=='OPPORTUNITY_BRIEF_V2' else 'PlaneByte digital review.pdf')
    catalog=body.get('catalog_snapshot') or {}
    if catalog.get('catalog_attached'):
        from app.experiments.runtime import catalog_attachment
        content=catalog_attachment(c,pid,body)
        message.add_attachment(content,maintype='application',subtype='pdf',filename='PlaneByte Product Catalog.pdf')
    key=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,intended_to,subject,body_text,in_reply_to,references_json,report_id,created_at,idempotency_key,content_hash,test_mode) VALUES(?,?,?,?,?,'OUTBOUND','SENDING',?,?,?,?,?,?,?,?,?,?,?,?)",(key,pid,acc['id'],thread,str(message['Message-ID']),s.from_address,result['to_address'],result['intended_to'],result['subject'],result['body_text'],reply_to,json.dumps(references),body.get('report_id'),stamp,body['idempotency_key'],content_hash,int(result['test_mode'])))
    if acc['provider']=='gmail_oauth':c.execute('UPDATE email_messages SET mailbox_revision=? WHERE id=?',(acc['mailbox_revision'],key))
    c.execute('UPDATE email_messages SET template_id=?,message_type=?,track_opens=?,track_clicks=? WHERE id=?',(body.get('template_id'),'OWNER_CONTROLLED_REDIRECT' if redirected else body.get('message_type','FIRST_CONTACT'),int(result['track_opens']),int(result['track_clicks']),key))
    plain,rich,optout=tracking.render_message(c,key,text,result['track_opens'],result['track_clicks'],seed=render_seed(result['preview_token']) if body.get('preview_nonce') else None)
    # Keep the alternative inside multipart/mixed when the reviewed PDF is attached.
    target=message.get_payload(0) if message.get_content_type()=='multipart/mixed' else message
    target.set_content(plain);target.add_alternative(rich,subtype='html')
    if (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=10:
        c.execute('UPDATE email_messages SET rendered_html=?,rendered_text=? WHERE id=?',(rich,plain,key))
    message['List-Unsubscribe']='<'+optout+'>'
    message['List-Unsubscribe-Post']='List-Unsubscribe=One-Click'
    if redirected:activity(c,pid,actor,'OWNER_CONTROLLED_REDIRECT',{'message_id':key,'actual_recipient':controlled_envelope_to,'intended_recipient':result['intended_to'],'authorization':controlled_authorization,'report_id':body.get('report_id'),'real_prospect_contacted':False},'controlled-'+key)
    if body.get('experiment_member_id'):
        from app.experiments.service import message_hook
        message_hook(c,key,body)
    from app.database.contactable_schema import ready as contactable_ready
    if contactable_ready(c):
        from app.mail.contacted import organization
        c.execute('UPDATE email_messages SET organization_id=?,campaign_id=?,template_version=?,pdf_asset_id=?,pdf_version=?,outreach_strategy=? WHERE id=?',(organization(),body.get('campaign_id'),body.get('template_version'),body.get('pdf_asset_id'),body.get('pdf_version'),body.get('outreach_strategy'),key))
    c.commit() # Reserve before SMTP. An uncertain result is never automatically resent.
    # Recheck suppression under the canonical lock immediately before SMTP.
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)')
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    from app.mail.contacted import ensure_new
    try:ensure_new(c,result['to_address'],idempotency_key=body['idempotency_key'])
    except HTTPException:
        c.execute("UPDATE email_messages SET status='FAILED',error_code='PERMANENT_RECIPIENT_GUARD' WHERE id=?",(key,));c.commit();raise
    if suppressed(c,pid):c.execute("UPDATE email_messages SET status='FAILED',error_code='SUPPRESSED' WHERE id=?",(key,));c.commit();raise HTTPException(409,'This prospect is marked Do Not Contact.')
    # Repeat the reviewed recipient/account/report/config checks after reservation.
    try:
        final=preview(c,pid,actor,body)
        if not hmac.compare_digest(final['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Configuration changed. Review a fresh preview.')
        transport=transport_for(c,acc)
        if not final['test_mode']:
            health=transport.health_check()
            if health.get('smtp')!='READY':raise HTTPException(503,'SMTP sending is not ready. Test the connection before sending.')
        # Refresh the reviewed checks after the potentially slow health connection.
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)');c.execute('SELECT pg_advisory_xact_lock(691944410)')
        elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
        final=preview(c,pid,actor,body)
        if not hmac.compare_digest(final['preview_token'],body.get('preview_token','')):raise HTTPException(409,'Review a fresh preview after the configuration change.')
        limit=settings_for(c,acc);stamp=datetime.now(timezone.utc)
        for span,maximum in [(timedelta(hours=1),limit.max_hour),(timedelta(days=1),limit.max_day)]:
            reserved=c.execute("SELECT COUNT(*) FROM email_messages WHERE organization_id=? AND direction='OUTBOUND' AND status IN ('SENDING','SENT','UNCERTAIN') AND created_at>=?",(organization(),(stamp-span).isoformat())).fetchone()[0]
            if reserved>maximum:raise HTTPException(429,'The configured sending limit has been reached.')
        # The canonical lock remains held across this final check and SMTP.
        if suppressed(c,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
        if body.get('experiment_member_id') and not redirected:
            send_gate(c,body,reserved=True)
        if acc['provider']=='gmail_oauth' and body.get('workflow_run_id'):validate_execution(c,body['workflow_run_id'],acc['id'])
        delivery_id=transport.send_message(message)
        if acc['provider']=='gmail_oauth':c.execute('UPDATE email_messages SET provider_delivery_id=? WHERE id=? AND organization_id=?',(delivery_id,key,organization()))
    except HTTPException:
        c.execute("UPDATE email_messages SET status='FAILED',error_code='FINAL_SAFETY_CHECK' WHERE id=?",(key,));tracking.event(c,key,'SEND_FAILED',metadata={'reason':'FINAL_SAFETY_CHECK'});c.commit();raise
    except SendFailed:
        c.execute("UPDATE email_messages SET status='FAILED',error_code='SMTP_REJECTED_OR_CONNECTION' WHERE id=?",(key,));tracking.event(c,key,'SEND_FAILED',metadata={'reason':'SMTP_REJECTED_OR_CONNECTION'});c.commit();return {'id':key,'status':'FAILED','detail':'Email could not be sent. Review the account connection before trying a new message.'}
    except Exception:
        c.execute("UPDATE email_messages SET error_code='SMTP_RESULT_UNCERTAIN' WHERE id=?",(key,));c.commit();return {'id':key,'status':'SENDING','detail':'Send outcome is uncertain. Check the mailbox before sending again; automatic retries are blocked.'}
    c.execute("UPDATE email_messages SET status='SENT',sent_at=? WHERE id=?",(now(),key));c.execute("UPDATE email_threads SET last_message_at=?,last_direction='OUTBOUND' WHERE id=?",(now(),thread));ensure(c,pid)
    from app.mail.contacted import record_message
    record_message(c,key)
    if not redirected:c.execute('UPDATE prospect_sales SET last_contact_at=? WHERE prospect_id=?',(now(),pid))
    tracking.event(c,key,'SMTP_ACCEPTED')
    activity(c,pid,actor,'EMAIL_SENT',{'message_id':key,'to':result['to_address'],'intended_to':result['intended_to'],'subject':result['subject'],'report_id':body.get('report_id'),'test_mode':result['test_mode']},'sent-'+key)
    current=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
    if current=='READY_TO_CONTACT' and not redirected:ProspectRepository(c).workflow(pid,actor,lead_status='CONTACTED')
    if body.get('followup_days') and not redirected:schedule(c,pid,actor,(datetime.now(timezone.utc)+timedelta(days=body['followup_days'])).isoformat(),reason='Scheduled after reviewed email send')
    c.commit();return {'id':key,'status':'SENT','thread_id':thread,'test_mode':result['test_mode'],'provider_message_id':str(message['Message-ID']),'owner_controlled_redirect':redirected}

def match_reply(c,incoming,*,account_id=None):
    from app.platform.context import current
    acc=account(c,current().actor,account_id)
    refs=incoming.get('references',[])[:30]
    if not refs:return None
    from app.platform.context import organization
    rows=c.execute("SELECT id,prospect_id,thread_id,to_address,created_at,provider_message_id,message_type,test_mode FROM email_messages WHERE organization_id=? AND account_id=? AND direction='OUTBOUND' AND status='SENT' AND provider_message_id IN ("+','.join('?' for _ in refs)+')',[organization(),acc['id'],*refs]).fetchall()
    if not rows or len({r['thread_id'] for r in rows})!=1:return None
    senders=[v.lower() for _,v in getaddresses([incoming['from']])];targets={v.lower() for _,v in getaddresses([incoming['to']])}
    mailbox=acc['email_address'] if acc['provider']=='gmail_oauth' else mail_settings().from_address
    if len(senders)!=1 or senders[0] not in {r['to_address'].lower() for r in rows} or mailbox.lower() not in targets:return None
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
    if authority!='mx.google.com' and not any(authority==host or authority.endswith('.'+host) for host in ('hostinger.com','hostinger.io','titan.email','mailchannels.net')):return False
    senders=getaddresses([incoming.get('from','')])
    if len(senders)!=1 or '@' not in senders[0][1]:return False
    domain=senders[0][1].split('@',1)[1].lower()
    for clause in value.split(';'):
        if re.search(r'\bdmarc=pass\b',clause) and re.search(r'header\.from='+re.escape(domain)+r'(?:\s|$)',clause):return True
        if re.search(r'\bdkim=pass\b',clause) and re.search(r'header\.d='+re.escape(domain)+r'(?:\s|$)',clause):return True
    return False

def sync_mailbox(*, recheck=False,account_id=None):
    if account_id:
        from app.mail.customer import sync_mailbox as customer_sync
        return customer_sync(account_id,recheck=recheck)
    from app.platform.context import require_internal_mailbox,organization
    require_internal_mailbox()
    s=mail_settings()
    folder='ALL_MAIL' if s.provider=='gmail' else 'INBOX'
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
        from app.database.contactable_schema import ready as contacted_ready
        if contacted_ready(c):
            from app.mail.contacted import organization
            known.update(r[0] for r in c.execute('SELECT provider_message_id FROM contacted_recipient_sends WHERE organization_id=? AND provider_message_id IS NOT NULL ORDER BY sent_at DESC LIMIT 10000',(organization(),)).fetchall())
        if not known:return {'received':0,'reason':'No tracked outbound messages yet.'}
        row=c.execute("SELECT * FROM email_sync_state WHERE account_id=? AND folder=?",(ACCOUNT,folder)).fetchone();cursor=dict(row) if row and not recheck else {};c.commit()
        from app.database.experiment_schema import ready as experiment_ready
        if experiment_ready(c):
            cursor['experiment_auto_refs']=[r[0] for r in c.execute('SELECT m.provider_message_id FROM experiment_members a JOIN email_messages m ON m.id=a.message_id WHERE a.message_id IS NOT NULL').fetchall()]
            known.update(cursor['experiment_auto_refs']) # Preserve reply matching beyond the legacy2,000-message sample.
        messages,updated=provider().sync_messages(known,cursor);received=0
        if experiment_ready(c):
            from app.experiments.provider_capacity import refresh
            refresh(c)
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)')
        received=ingest_messages(c,messages,acc)
        c.execute("INSERT INTO email_sync_state(account_id,folder,uidvalidity,last_uid) VALUES(?,?,?,?) ON CONFLICT(account_id,folder) DO UPDATE SET uidvalidity=excluded.uidvalidity,last_uid=excluded.last_uid",(ACCOUNT,folder,updated.get('uidvalidity',''),max(updated.get('last_uid',0), row['last_uid'] if row and row['uidvalidity']==updated.get('uidvalidity') else 0)))
        c.execute('UPDATE email_accounts SET last_sync_at=?,updated_at=? WHERE id=?',(now(),now(),ACCOUNT));c.commit();return {'received':received,'checked':len(messages),'last_sync_at':now()}
    finally:
        if getattr(c,'backend',None)!='postgres':
            c.execute('DELETE FROM email_sync_lock WHERE owner=?',(owner,));c.commit()
        c.close()


def ingest_messages(c,messages,acc):
    """Shared durable reply/DSN processing after provider and mailbox ownership checks."""
    from app.platform.context import organization
    s=settings_for(c,acc);received=0;org=organization()
    for incoming in messages[:30]:
        if incoming.get('kind')=='dsn':
            bounces.process(c,incoming,account_id=acc['id']);continue
        if not re.fullmatch(r'<[^<>\s]{3,250}>',incoming.get('message_id','')):continue
        match=match_reply(c,incoming,account_id=acc['id'])
        if not match:
            if acc['provider']!='gmail_oauth':
                from app.mail.contacted import archived_reply
                archived_reply(c,incoming)
            continue
        pid=match['prospect_id'];thread=match['thread_id'];key=str(uuid.uuid4());stamp=now()
        changed=c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,references_json,created_at,received_at,test_mode,organization_id) VALUES(?,?,?,?,?,'INBOUND','RECEIVED',?,?,?,?,?,?,?,?,?) ON CONFLICT(account_id,provider_message_id) DO NOTHING",(key,pid,acc['id'],thread,incoming['message_id'],getaddresses([incoming['from']])[0][1],acc['email_address'],incoming['subject'],incoming['body_text'],json.dumps(incoming['references']),stamp,stamp,int(bool(match['test_mode']) or s.mode=='test'),org)).rowcount
        if not changed:
            existing=c.execute('SELECT id,prospect_id,thread_id FROM email_messages WHERE account_id=? AND provider_message_id=? AND organization_id=?',(acc['id'],incoming['message_id'],org)).fetchone()
            if not existing or existing['prospect_id']!=pid or existing['thread_id']!=thread:continue
            key=existing['id']
            if c.execute('SELECT 1 FROM activities WHERE dedup_key=? AND organization_id=?',('reply-'+key,org)).fetchone():continue
        verified=authenticated_reply(incoming)
        if verified and acc['provider']!='gmail_oauth':
            from app.database.experiment_schema import ready as experiment_ready
            if experiment_ready(c):
                from app.experiments.service import inbound_hook
                inbound_hook(c,match['id'],key,incoming['body_text'],automatic=incoming.get('automatic',False))
            template=c.execute('SELECT template_id FROM email_messages WHERE id=?',(match['id'],)).fetchone()[0]
            if template and template.startswith('PB_INTRO_'):
                from app.experiments.service import classify
                disposition=classify(incoming.get('text','') or incoming.get('body_text',''))
                if disposition in ('POSITIVE','NEGATIVE'):tracking.event(c,match['id'],disposition+'_REPLY',dedup=disposition+':'+key,metadata={'inbound_message_id':key})
        if verified and tracking.preferences(c)['track_replies']:tracking.event(c,match['id'],'REPLIED_VERIFIED',dedup='verified-'+key,metadata={'inbound_message_id':key})
        if not changed and not verified:continue
        received+=int(bool(changed));c.execute("UPDATE email_threads SET last_message_at=?,last_direction='INBOUND' WHERE id=? AND organization_id=?",(stamp,thread,org));ensure(c,pid)
        if verified:c.execute('UPDATE prospect_sales SET unread_replies=unread_replies+1 WHERE prospect_id=? AND organization_id=?',(pid,org))
        activity(c,pid,'system','EMAIL_RECEIVED',{'message_id':key,'reply_verified':verified,'test_mode':s.mode=='test'},'received-'+key)
        if verified:
            c.execute('UPDATE activities SET metadata_json=? WHERE dedup_key=? AND organization_id=?',(json.dumps({'message_id':key,'reply_verified':True,'test_mode':s.mode=='test'}),'received-'+key,org))
            activity(c,pid,'system','REPLY_DETECTED',{'message_id':key,'match':'Message-ID references + peer address + mailbox + time window + aligned provider authentication','test_mode':s.mode=='test'},'reply-'+key)
        if verified and match['message_type']!='OWNER_CONTROLLED_REDIRECT' and (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=9:
            c.execute("UPDATE master_lead_state SET contact_state='REPLIED',sales_state=CASE WHEN sales_state IN ('MEETING','PROPOSAL','WON','LOST') THEN sales_state ELSE 'REPLIED' END,updated_at=? WHERE prospect_id=? AND organization_id=?",(now(),pid,org))
            c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND prospect_id IN (SELECT id FROM prospects WHERE organization_id=?) AND status='QUEUED'",(pid,org))
        status=c.execute('SELECT lead_status FROM prospects WHERE id=? AND organization_id=?',(pid,org)).fetchone()[0]
        if verified and match['message_type']!='OWNER_CONTROLLED_REDIRECT' and status in ('CONTACTED','FOLLOW_UP') and not suppressed(c,pid):ProspectRepository(c).workflow(pid,'system',lead_status='REPLIED')
    return received


def sync_internal_mailbox(*, recheck=False):
    """Worker entry for the existing mailbox, using its persisted active owner."""
    from app.platform.context import workspace_scope,require_internal_mailbox
    with db_session() as scope_conn:
        acc=scope_conn.execute('SELECT user_id,organization_id FROM email_accounts WHERE id=?',(ACCOUNT,)).fetchone()
        if not acc or not acc['organization_id']:
            return {'status':'NOT_CONFIGURED','received':0}
        with workspace_scope(scope_conn,acc['user_id'],acc['organization_id']):
            require_internal_mailbox()
            return sync_mailbox(recheck=recheck)
