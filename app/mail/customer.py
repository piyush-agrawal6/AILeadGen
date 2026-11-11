"""Owned mailbox selection/policy and Gmail transport; no internal credential fallback."""
import asyncio,base64,contextvars,json,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from email import policy as mime_policy
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import organization,current
from app.api.organization import require_role
from app.integrations import gmail,service as connections
from app.mail.config import MailSettings
from app.mail.providers import SendFailed,SendUncertain

def owned_account(c,actor,account_id=None):
    gmail.require_enabled();org=organization()
    context=current()
    if actor!=context.actor:raise HTTPException(403,'Use the verified mailbox owner identity.')
    if actor not in get_settings().allowed_emails:
        from app.platform.admission import access
        if not access(c,actor):raise HTTPException(403,'The customer account is unavailable.')
    require_role(c,context.actor,org,('OWNER','ADMIN'))
    where=' AND a.id=?' if account_id else '';args=(account_id,) if account_id else ()
    row=c.execute('''SELECT a.*,g.id AS connection_id,g.revision AS mailbox_revision,g.status AS connection_status,
        g.owner_user_id,g.credentials_ciphertext FROM email_accounts a JOIN customer_gmail_connections g ON g.account_id=a.id
        WHERE a.organization_id=? AND g.organization_id=? AND a.user_id=? AND g.owner_user_id=?'''+where,
        (org,org,actor,actor)+args).fetchone()
    if not row:raise HTTPException(404,'Connect your own Gmail account for this workspace.')
    acc=dict(row);acc.pop('credentials_ciphertext',None)
    return acc

def policy(c):
    gmail.require_enabled();org=organization()
    row=c.execute('SELECT * FROM customer_mail_policies WHERE organization_id=?',(org,)).fetchone()
    return dict(row) if row else {'organization_id':org,'revision':0,'sending_approved':0,'approved_by':None,'approved_at':None,'max_hour':5,'max_day':50,'updated_at':None}

class PolicyUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=0)
    max_hour:int=Field(ge=1,le=10)
    max_day:int=Field(ge=1,le=100)
    confirmation:Literal['APPROVE_SENDING','DISABLE_SENDING']

def save_policy(c,body):
    gmail.require_enabled();org=organization();require_role(c,current().actor,org,('OWNER',));connections.lock(c)
    previous=policy(c)
    if previous['revision']!=body.revision:raise HTTPException(409,'Sending policy changed. Review the current settings.')
    connection=c.execute('SELECT id,status,account_id FROM customer_gmail_connections WHERE organization_id=?',(org,)).fetchone()
    if not connection:raise HTTPException(409,'Connect a Gmail mailbox before approving sending.')
    if body.confirmation=='APPROVE_SENDING' and connection['status']!='CONNECTED':
        raise HTTPException(409,'Connect and verify your Gmail mailbox before approving sending.')
    stamp=now();approved=int(body.confirmation=='APPROVE_SENDING')
    c.execute('''INSERT INTO customer_mail_policies(organization_id,revision,sending_approved,approved_by,approved_at,max_hour,max_day,updated_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET revision=excluded.revision,sending_approved=excluded.sending_approved,
        approved_by=excluded.approved_by,approved_at=excluded.approved_at,max_hour=excluded.max_hour,max_day=excluded.max_day,updated_at=excluded.updated_at''',
        (org,previous['revision']+1,approved,current().actor if approved else None,stamp if approved else None,body.max_hour,body.max_day,stamp))
    connections.audit(c,connection['id'],'CUSTOMER_MAIL_APPROVED' if approved else 'CUSTOMER_MAIL_DISABLED')
    return policy(c)

def settings(c,acc):
    s=get_settings();p=policy(c);org=organization()
    company=c.execute('SELECT name FROM organizations WHERE id=?',(org,)).fetchone()[0]
    # Construct a credential-free settings object; never read global Gmail/SMTP
    # environment settings as customer connection authority or sender identity.
    from app.api.organization import membership_role
    approved=bool(p['sending_approved'] and membership_role(c,p['approved_by'],org)=='OWNER')
    return MailSettings.model_construct(provider='gmail_oauth',from_name=company,from_address=acc['email_address'],username='',gmail_username='',
        company=company,website='',mode=s.heysow_customer_mail_mode,test_recipient=s.heysow_customer_mail_test_recipient,
        sending_enabled=bool(s.heysow_customer_mail_sending_enabled and approved),
        live_approved=s.heysow_customer_mail_live_approved,max_hour=p['max_hour'],max_day=p['max_day'],auto_email_enabled=s.heysow_customer_mail_schedules_enabled,
        tracking_enabled=False,tracking_base_url='',signature_name=company,signature_role='',sync_enabled=True)

def can_send(c,acc,s=None):
    s=s or settings(c,acc)
    mode_ready=bool(s.mode=='test' and s.test_recipient and not s.live_approved or s.mode=='production' and s.live_approved and get_settings().app_env=='production')
    return bool(s.sending_enabled and mode_ready and acc['status']=='CONNECTED' and acc['connection_status']=='CONNECTED')

def validate_campaign(c,campaign_id,account_id):
    row=c.execute('SELECT email_account_id FROM scan_campaigns WHERE id=? AND organization_id=?',(campaign_id,organization())).fetchone()
    if not row:raise HTTPException(404,'Campaign not found in this workspace.')
    if row['email_account_id']!=account_id:raise HTTPException(409,'Route this campaign to the reviewed workspace mailbox before sending.')

def validate_execution(c,run_id,account_id):
    row=c.execute("SELECT created_by,configuration_json,campaign_id FROM workflow_runs WHERE id=? AND organization_id=? AND kind='OUTREACH' AND status='RUNNING'"+(' FOR UPDATE' if getattr(c,'backend',None)=='postgres' else ''),(run_id,organization())).fetchone()
    if not row or row['created_by']!=current().actor or json.loads(row['configuration_json']).get('account_id')!=account_id:
        raise HTTPException(409,'The approved customer outreach run is paused, changed or unavailable.')
    validate_campaign(c,row['campaign_id'],account_id)

def reserve_spacing(c,acc):
    connections.lock(c);p=policy(c)
    if p.get('next_send_at') and p['next_send_at']>now():raise HTTPException(429,'Wait for the workspace mailbox sending interval.')
    from app.mail.limits import MIN_SPACING_SECONDS
    c.execute('UPDATE customer_mail_policies SET next_send_at=? WHERE organization_id=?',((datetime.now(timezone.utc)+timedelta(seconds=MIN_SPACING_SECONDS)).isoformat(),organization()))

def route_campaign(c,campaign_id,account_id):
    acc=owned_account(c,current().actor,account_id);connections.lock(c)
    campaign=c.execute('SELECT email_account_id FROM scan_campaigns WHERE id=? AND organization_id=?',(campaign_id,organization())).fetchone()
    if not campaign:raise HTTPException(404,'Campaign not found in this workspace.')
    if acc['connection_status']!='CONNECTED' or acc['status']!='CONNECTED':raise HTTPException(409,'Connect the mailbox before routing this campaign.')
    if c.execute("SELECT 1 FROM workflow_runs WHERE campaign_id=? AND organization_id=? AND kind='OUTREACH' AND status IN ('RUNNING','PREPARING')",(campaign_id,organization())).fetchone():
        raise HTTPException(409,'Pause active outreach before changing its mailbox route.')
    c.execute('UPDATE scan_campaigns SET email_account_id=? WHERE id=? AND organization_id=?',(account_id,campaign_id,organization()))
    if campaign['email_account_id']!=account_id:
        c.execute("UPDATE outreach_run_items SET status='NEEDS_REVIEW',error='Campaign mailbox route changed. Review a new preview.' WHERE organization_id=? AND run_id IN (SELECT id FROM workflow_runs WHERE campaign_id=? AND organization_id=?) AND status='READY'",(organization(),campaign_id,organization()))
    connections.audit(c,acc['connection_id'],'CAMPAIGN_MAILBOX_ROUTED')
    return {'campaign_id':campaign_id,'account_id':account_id}

def run(coroutine,timeout=60):
    """Bridge the existing synchronous mail engine to bounded async OAuth I/O."""
    async def bounded():return await asyncio.wait_for(coroutine,timeout=timeout)
    try:asyncio.get_running_loop()
    except RuntimeError:return asyncio.run(bounded())
    context=contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(context.run,asyncio.run,bounded()).result(timeout=timeout+1)

class GmailProvider:
    def __init__(self,c,acc):
        self.c=c;self.acc=acc
        self.token,self.revision=run(connections.access_token(c,acc['connection_id'],spec=gmail.spec()))

    def validate(self):
        acc=owned_account(self.c,current().actor,self.acc['id'])
        if acc['connection_status']!='CONNECTED' or acc['status']!='CONNECTED' or acc['mailbox_revision']!=self.revision:
            raise HTTPException(409,'Mailbox connection changed. Review and reconnect before sending.')

    def health_check(self):
        self.validate()
        result=run(gmail.health(self.c,self.acc['connection_id']))
        return {'smtp':result['sending'],'imap':result['inbox']}

    def send_message(self,message):
        from app.mail.service import address
        self.validate();s=settings(self.c,self.acc)
        if not s.sending_enabled:raise SendFailed('CUSTOMER_SENDING_DISABLED')
        if s.mode=='production' and (get_settings().app_env!='production' or not s.live_approved):raise SendFailed('LIVE_SENDING_NOT_APPROVED')
        if s.mode=='test' and (not s.test_recipient or address(str(message['To']))!=address(s.test_recipient)):raise SendFailed('CONTROLLED_RECIPIENT_REQUIRED')
        from email.utils import getaddresses
        if getaddresses(message.get_all('From',[]))!=[(s.from_name,s.from_address)]:raise SendFailed('MAILBOX_SENDER_MISMATCH')
        encoded=base64.urlsafe_b64encode(message.as_bytes(policy=mime_policy.SMTP)).decode()
        try:result=run(gmail.api('POST','messages/send',self.token,payload={'raw':encoded}))
        except gmail.GmailRejected as exc:
            if exc.status in (401,403):
                row=connections.owned(self.c,self.acc['connection_id'],spec=gmail.spec())
                connections.provider_error(self.c,row,'GMAIL_AUTH_REJECTED',reauth=True,spec=gmail.spec())
            if exc.status in (400,401,403,404,429):raise SendFailed('GMAIL_REJECTED') from None
            raise SendUncertain('GMAIL_RESULT_UNCERTAIN') from None
        except Exception:raise SendUncertain('GMAIL_RESULT_UNCERTAIN') from None
        identifier=result.get('id')
        if not isinstance(identifier,str) or not re_full_id(identifier):raise SendUncertain('GMAIL_RESULT_UNCERTAIN')
        return identifier

    def sync_messages(self,known_ids,cursor,permit=None):
        self.validate()
        return run(asyncio.wait_for(gmail.sync_messages(self.token,known_ids,cursor,permit=permit),timeout=45))

def re_full_id(value):
    import re
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value))

def sync_mailbox(account_id,*,recheck=False):
    from app.database.connection import db_session
    from app.mail import service
    gmail.require_enabled();org=organization();lease=str(uuid.uuid4())
    with db_session() as c:
        acc=owned_account(c,current().actor,account_id);row=connections.owned(c,acc['connection_id'],spec=gmail.spec())
        if acc['connection_status']!='CONNECTED' or acc['status']!='CONNECTED':raise HTTPException(409,'Reconnect this Gmail mailbox before synchronizing.')
        connections.lock(c)
        previous=c.execute('SELECT * FROM customer_gmail_sync WHERE connection_id=? AND organization_id=?',(row['id'],org)).fetchone()
        stamp=now()
        if previous and previous['lease_until'] and previous['lease_until']>stamp:return {'status':'BUSY','received':0}
        if previous and not recheck and (previous['attempts']>=3 or previous['next_attempt_at'] and previous['next_attempt_at']>stamp):return {'status':'RETRY_DEFERRED','received':0}
        c.execute('''INSERT INTO customer_gmail_sync(connection_id,organization_id,lease_id,lease_until) VALUES(?,?,?,?)
            ON CONFLICT(connection_id) DO UPDATE SET lease_id=excluded.lease_id,lease_until=excluded.lease_until WHERE customer_gmail_sync.organization_id=excluded.organization_id''',
            (row['id'],org,lease,(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat()))
        cursor={} if recheck else json.loads(previous['cursor_json']) if previous else {}
        known={entry[0] for entry in c.execute("SELECT provider_message_id FROM email_messages WHERE organization_id=? AND account_id=? AND direction='OUTBOUND' AND status='SENT' ORDER BY created_at DESC LIMIT 10000",(org,account_id)).fetchall()}
        c.commit()
        try:
            transport=GmailProvider(c,acc)
            def permit():
                transport.validate()
                active=c.execute('SELECT lease_id,lease_until FROM customer_gmail_sync WHERE connection_id=? AND organization_id=?',(row['id'],org)).fetchone()
                if not active or active['lease_id']!=lease or not active['lease_until'] or active['lease_until']<=now():raise HTTPException(409,'Inbox synchronization lease expired or was replaced.')
            messages,updated=transport.sync_messages(known,cursor,permit)
            connections.lock(c);transport.validate()
            if not c.execute('UPDATE customer_gmail_sync SET lease_id=lease_id WHERE connection_id=? AND organization_id=? AND lease_id=? AND lease_until>?',(row['id'],org,lease,now())).rowcount:raise HTTPException(409,'This synchronization lease expired or was replaced.')
            received=service.ingest_messages(c,messages,acc)
            c.execute('''UPDATE customer_gmail_sync SET cursor_json=?,last_success_at=?,attempts=0,next_attempt_at=NULL,
                last_error_code=NULL,lease_id=NULL,lease_until=NULL WHERE connection_id=? AND organization_id=? AND lease_id=?''',(json.dumps(updated),now(),row['id'],org,lease))
            c.execute('UPDATE email_accounts SET last_sync_at=?,updated_at=? WHERE id=? AND organization_id=?',(now(),now(),account_id,org));c.commit()
            return {'status':'SYNCED','received':received,'checked':len(messages),'last_sync_at':now()}
        except Exception as exc:
            c.rollback();attempts=(previous['attempts'] if previous else 0)+1
            if isinstance(exc,gmail.IdentityChanged) or isinstance(exc,gmail.GmailRejected) and exc.status in (401,403):
                connections.provider_error(c,row,'GMAIL_AUTH_REJECTED',reauth=True,spec=gmail.spec())
            retryable=(exc.status==429 or exc.status>=500) if isinstance(exc,gmail.GmailRejected) else not isinstance(exc,HTTPException) or exc.status_code in (429,503)
            if isinstance(exc,gmail.IdentityChanged):retryable=False
            code='GMAIL_HISTORY_EXPIRED' if isinstance(exc,gmail.HistoryExpired) else 'GMAIL_SYNC_TEMPORARY' if retryable else 'GMAIL_SYNC_REVIEW_REQUIRED'
            attempts=min(attempts,3) if retryable else 3
            c.execute('''UPDATE customer_gmail_sync SET lease_id=NULL,lease_until=NULL,attempts=?,next_attempt_at=?,last_error_code=?
                WHERE connection_id=? AND organization_id=? AND lease_id=?''',(attempts,(datetime.now(timezone.utc)+timedelta(seconds=30*2**attempts)).isoformat() if retryable and attempts<3 else None,code,row['id'],org,lease));c.commit()
            raise HTTPException(503 if retryable else 409,'Gmail synchronization needs a retry or connection review. The saved cursor was retained.') from None

def sync_owned_account(account_id):
    """Worker context is recovered from the persisted mailbox, never the caller's org."""
    from app.database.connection import db_session
    from app.platform.context import workspace_scope
    gmail.require_enabled()
    with db_session() as c:
        row=c.execute('SELECT organization_id,owner_user_id FROM customer_gmail_connections WHERE account_id=?',(account_id,)).fetchone()
        if not row:raise HTTPException(404,'Mailbox not found.')
        try:caller=current()
        except HTTPException:caller=None
        if caller and (caller.organization_id!=row['organization_id'] or caller.actor!=row['owner_user_id']):
            raise HTTPException(404,'Mailbox not found in this caller workspace.')
        with workspace_scope(c,row['owner_user_id'],row['organization_id']):return sync_mailbox(account_id)

def retry_sync(c,connection_id,revision):
    row=connections.owned(c,connection_id,spec=gmail.spec());acc=owned_account(c,current().actor,row['account_id'])
    connections.lock(c)
    row=connections.owned(c,connection_id,spec=gmail.spec())
    if row['revision']!=revision or row['status']!='CONNECTED':raise HTTPException(409,'Review the current connected mailbox before retrying inbox sync.')
    state=c.execute('SELECT lease_until,last_error_code FROM customer_gmail_sync WHERE connection_id=? AND organization_id=?',(connection_id,organization())).fetchone()
    if state and state['lease_until'] and state['lease_until']>now():raise HTTPException(409,'Inbox synchronization is already running.')
    if state and state['last_error_code']=='GMAIL_HISTORY_EXPIRED':raise gmail.HistoryExpired()
    c.execute('UPDATE customer_gmail_sync SET attempts=0,next_attempt_at=NULL,last_error_code=NULL WHERE connection_id=? AND organization_id=?',(connection_id,organization()));c.commit()
    # Retry resumes the durable cursor; resetting history is a different operation.
    return sync_mailbox(acc['id'])

def restart_sync(c,connection_id,revision):
    connections.lock(c);row=connections.owned(c,connection_id,spec=gmail.spec())
    acc=owned_account(c,current().actor,row['account_id'])
    if row['revision']!=revision or row['status']!='CONNECTED':raise HTTPException(409,'Review the current mailbox before restarting recent inbox sync.')
    state=c.execute('SELECT lease_until,last_error_code FROM customer_gmail_sync WHERE connection_id=? AND organization_id=?',(connection_id,organization())).fetchone()
    if not state or state['last_error_code']!='GMAIL_HISTORY_EXPIRED':raise HTTPException(409,'Recent sync restart is available only after Gmail history expires.')
    if state['lease_until'] and state['lease_until']>now():raise HTTPException(409,'Inbox synchronization is already running.')
    c.execute("UPDATE customer_gmail_sync SET cursor_json='{}',attempts=0,next_attempt_at=NULL,last_error_code=NULL WHERE connection_id=? AND organization_id=?",(connection_id,organization()))
    connections.audit(c,connection_id,'GMAIL_RECENT_SYNC_RESTARTED');c.commit()
    return sync_mailbox(acc['id'])

def outreach_tick(c,run_id):
    """One owned reviewed item per tick; only pre-reservation throttling is retried."""
    from app.platform.context import workspace_scope
    from app.mail import service
    gmail.require_enabled();org=organization()
    run_row=c.execute("SELECT * FROM workflow_runs WHERE id=? AND organization_id=? AND kind='OUTREACH' AND status='RUNNING'",(run_id,org)).fetchone()
    if not run_row:return {'status':'NO_EXPLICIT_RUN'}
    if run_row['created_by']!=current().actor:raise HTTPException(403,'This customer outreach belongs to another mailbox owner.')
    with workspace_scope(c,run_row['created_by'],org):
        options=json.loads(run_row['configuration_json']);acc=owned_account(c,current().actor,options.get('account_id'))
        s=settings(c,acc)
        if not s.sending_enabled or run_row['schedule_id'] and not s.auto_email_enabled:return {'status':'DISABLED'}
        from app.workflows.controls import require_unpaused
        try:require_unpaused(c,'email')
        except HTTPException:return {'status':'PAUSED'}
        connections.lock(c);validate_execution(c,run_id,acc['id'])
        item=c.execute("SELECT * FROM outreach_run_items WHERE run_id=? AND organization_id=? AND status='READY' AND (next_mail_attempt_at IS NULL OR next_mail_attempt_at<=?) ORDER BY created_at,id LIMIT 1",(run_id,org,now())).fetchone()
        if not item:return {'status':'EMPTY'}
        from zoneinfo import ZoneInfo
        business=c.execute('SELECT city,country FROM businesses WHERE id=? AND prospect_id=?',(item['business_id'],item['prospect_id'])).fetchone()
        zones={'United Kingdom':'Europe/London','Germany':'Europe/Berlin','France':'Europe/Paris','India':'Asia/Kolkata','Australia':'Australia/Sydney','Canada':'America/Toronto','United States':'America/New_York'}
        local=datetime.now(timezone.utc).astimezone(ZoneInfo(zones.get(business['country'],'UTC') if options.get('recipient_timezone',True) else 'UTC'))
        if local.weekday()>=5 or not options.get('window_start','09:00')<=local.strftime('%H:%M')<options.get('window_end','17:00'):return {'status':'OUTSIDE_BUSINESS_HOURS'}
        body=json.loads(item['payload_json']);body.update(workflow_run_id=run_id)
        if body.get('account_id')!=acc['id']:raise HTTPException(409,'Review the item using this campaign mailbox.')
        c.commit()
        try:
            result=service.send(c,item['prospect_id'],current().actor,body)
            status='SENT' if result['status']=='SENT' else 'NEEDS_REVIEW'
            c.execute('UPDATE outreach_run_items SET status=?,message_id=?,error=?,next_mail_attempt_at=NULL WHERE id=? AND organization_id=?',(status,result['id'],None if status=='SENT' else 'Delivery outcome needs mailbox review.',item['id'],org));c.commit()
            return {'status':status}
        except HTTPException as exc:
            c.rollback()
            reserved=c.execute('SELECT id FROM email_messages WHERE idempotency_key=? AND organization_id=?',(item['idempotency_key'],org)).fetchone()
            attempts=item['mail_attempts']+1
            retryable=exc.status_code==429 and not reserved and attempts<3
            c.execute('UPDATE outreach_run_items SET status=?,mail_attempts=?,next_mail_attempt_at=?,error=? WHERE id=? AND organization_id=?',
                ('READY' if retryable else 'NEEDS_REVIEW',attempts,(datetime.now(timezone.utc)+timedelta(seconds=120*2**attempts)).isoformat() if retryable else None,'Mailbox limit reached.' if retryable else 'Sending authorization or content needs review.',item['id'],org));c.commit()
            return {'status':'RATE_LIMITED' if retryable else 'NEEDS_REVIEW'}

def advance_run(c,run_row):
    from app.platform.context import workspace_scope
    from app.workflows import service as workflows
    org=organization();gmail.require_enabled()
    run_row=workflows.row(c,run_row['id'])
    if run_row['kind']!='OUTREACH' or run_row['status'] not in ('PREPARING','DRAFT','RUNNING'):return
    with workspace_scope(c,run_row['created_by'],org):
        options=json.loads(run_row['configuration_json']);acc=owned_account(c,current().actor,options.get('account_id'));s=settings(c,acc)
        if run_row['schedule_id'] and not s.automatic_sending_enabled:return
        if run_row['status']=='PREPARING' or run_row['schedule_id'] and run_row['status']=='DRAFT':
            workflows.prepare(c,run_row['id'])
            if run_row['schedule_id'] and workflows.row(c,run_row['id'])['status']=='DRAFT':workflows.start(c,run_row['id'])
        if workflows.row(c,run_row['id'])['status']=='RUNNING':outreach_tick(c,run_row['id'])
        # Preparation is not approval. Never resume a manual draft or overwrite an
        # owner pause/cancellation observed after provider I/O.
        if workflows.row(c,run_row['id'])['status']!='RUNNING':return
        counts={row['status']:row['n'] for row in c.execute('SELECT status,COUNT(*) AS n FROM outreach_run_items WHERE run_id=? AND organization_id=? GROUP BY status',(run_row['id'],org)).fetchall()}
        pending=sum(counts.get(kind,0) for kind in ('READY','QUEUED','PREPARING'))
        status='RUNNING' if pending else 'NEEDS_REVIEW' if counts.get('NEEDS_REVIEW') else 'COMPLETED'
        c.execute('UPDATE workflow_runs SET result_count=?,status=?,completed_at=? WHERE id=? AND organization_id=?',
            (counts.get('SENT',0),status,None if pending or status=='NEEDS_REVIEW' else now(),run_row['id'],org));c.commit()
