"""Durable, encrypted, scoped transactional email. Never uses outreach sending flags."""
import base64,hashlib,html,json,re,time,uuid
from email.utils import parseaddr
from cryptography.fernet import Fernet,InvalidToken
from fastapi import HTTPException
import httpx
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.accounts import security

PURPOSES=frozenset(('SIGNUP_OTP','SIGNUP_NOTICE','SET_PASSWORD_OTP','PASSWORD_RESET','PASSWORD_CHANGED','TEAM_INVITATION','PAYMENT_CONFIRMED','RENEWAL_REMINDER','ACCESS_EXPIRED','WORKSPACE_NOTICE'))

def configured():
    s=get_settings();sender=s.resend_from_email
    address=parseaddr(sender)[1]
    return bool(s.resend_api_key.get_secret_value() and address.endswith('@planebyte.com') and re.fullmatch(r'[^\s@<>]+@planebyte\.com',address) and not any(char in sender for char in ('\r','\n','\x00')))

def require_enabled():
    if not get_settings().transactional_mail_enabled or not configured():raise HTTPException(503,'Account email delivery is temporarily unavailable. Retry later.')

def cipher():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'planebyte:transactional:v1:'+security.signing_key()).digest()))

def render(purpose,payload):
    if purpose in ('SIGNUP_OTP','SET_PASSWORD_OTP'):
        code=payload['code']
        if not re.fullmatch(r'\d{6}',code):raise ValueError('Invalid verification email payload.')
        subject='Your PlaneByte verification code'
        text=f'Your PlaneByte verification code is {code}. It expires in 10 minutes and works only with the signup or account request that generated it. Do not share this code. If you did not request it, ignore this email.'
    elif purpose=='SIGNUP_NOTICE':
        subject='Your PlaneByte sign-in request'
        text='If you already use PlaneByte, continue with your existing sign-in method at https://app.planebyte.com/login. This request does not change an existing password or link another sign-in method. If you did not request an account, ignore this email.'
    elif purpose=='PASSWORD_RESET':
        token=payload['token']
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise ValueError('Invalid password recovery payload.')
        subject='Reset your PlaneByte password'
        text='Use this one-time link within 20 minutes to reset your PlaneByte password: https://app.planebyte.com/reset-password?token='+token+'\nIf you did not request this, ignore this email. Your password has not changed.'
    elif purpose=='PASSWORD_CHANGED':
        subject='Your PlaneByte password changed'
        text='Your PlaneByte password was changed and existing customer sign-in sessions were revoked. If you did not make this change, use password recovery and contact PlaneByte support at contact@planebyte.com.'
    elif purpose=='TEAM_INVITATION':
        token=payload['token']
        if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}',token):raise ValueError('Invalid invitation email payload.')
        subject='You are invited to a PlaneByte workspace'
        text='You have been invited to '+payload['company']+'. Review and accept the invitation while signed in with this email address: https://app.planebyte.com/accept-invitation#'+token+'\nJoining requires verified sign-in and your explicit acceptance.'
    elif purpose=='PAYMENT_CONFIRMED':
        subject='Your PlaneByte payment is verified'
        text=payload['summary']+'\nView your payment receipt and access dates at https://app.planebyte.com/billing. This is a one-time purchase, not automatic renewal.'
    elif purpose in ('RENEWAL_REMINDER','ACCESS_EXPIRED'):
        subject='Your PlaneByte access '+('has expired' if purpose=='ACCESS_EXPIRED' else 'expires soon')
        text=payload['summary']+'\nYour saved research is retained. Review access and manual renewal at https://app.planebyte.com/billing. No automatic charge will be made.'
    elif purpose=='WORKSPACE_NOTICE':
        subject='A PlaneByte workspace update'
        text=payload['summary']+'\nReview your authorized workspace at https://app.planebyte.com/intent-radar.'
    else:raise ValueError('Unsupported transactional purpose.')
    if len(text)>5000:raise ValueError('Notification exceeds its bound.')
    return subject,text,'<div style="font-family:system-ui;line-height:1.6;max-width:600px">'+''.join('<p>'+html.escape(line)+'</p>' for line in text.split('\n'))+'</div>'

def queue(c,email,purpose,authority_id,payload,*,dedupe_key,expires_at,organization_id=None):
    require_enabled()
    if purpose not in PURPOSES or not 1<=len(dedupe_key)<=200:raise ValueError('Supported bounded notification required.')
    previous=c.execute('SELECT id FROM transactional_notifications WHERE dedupe_key=?',(dedupe_key,)).fetchone()
    if previous:return previous[0]
    subject,text,body=render(purpose,payload)
    key=str(uuid.uuid4());stamp=now()
    # Store the identical provider payload encrypted for safe idempotent retries;
    # remove it after acceptance/expiry. Verification records contain only hashes.
    mail={'from':get_settings().resend_from_email,'to':[email],'subject':subject,'text':text,'html':body,'headers':{'X-PlaneByte-Notification':key}}
    encrypted=cipher().encrypt(json.dumps(mail,separators=(',',':')).encode()).decode()
    c.execute("INSERT INTO transactional_notifications(id,account_email,organization_id,purpose,authority_id,dedupe_key,payload_encrypted,status,available_at,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'QUEUED',?,?,?,?)",(key,email,organization_id,purpose,authority_id,dedupe_key,encrypted,int(time.time()),expires_at,stamp,stamp))
    return key

def authorized(c,row):
    stamp=int(time.time());email=row['account_email'];purpose=row['purpose'];key=row['authority_id']
    if c.execute('SELECT 1 FROM transactional_suppressions WHERE account_email=?',(email,)).fetchone():return False
    if purpose in ('SIGNUP_OTP','SIGNUP_NOTICE','SET_PASSWORD_OTP'):
        expected='SIGNUP' if purpose in ('SIGNUP_OTP','SIGNUP_NOTICE') else 'SET_PASSWORD'
        return bool(c.execute('SELECT 1 FROM account_verifications WHERE id=? AND email=? AND purpose=? AND consumed_at IS NULL AND invalidated_at IS NULL AND attempts<5 AND expires_at>?',(key,email,expected,stamp)).fetchone())
    if purpose=='PASSWORD_RESET':
        return bool(c.execute("SELECT 1 FROM account_recovery_tokens r JOIN customer_accounts a ON a.user_id=r.user_id WHERE r.id=? AND a.email=? AND a.status='ACTIVE' AND a.password_hash IS NOT NULL AND r.consumed_at IS NULL AND r.expires_at>?",(key,email,stamp)).fetchone())
    if purpose=='PASSWORD_CHANGED':
        return bool(c.execute("SELECT 1 FROM account_recovery_tokens r JOIN customer_accounts a ON a.user_id=r.user_id WHERE r.id=? AND a.email=? AND a.status='ACTIVE' AND r.consumed_at IS NOT NULL",(key,email)).fetchone())
    if purpose=='TEAM_INVITATION':
        from app.api.organization import membership_role
        invitation=c.execute('SELECT * FROM workspace_invitations WHERE id=? AND organization_id=? AND email=?',(key,row['organization_id'],email)).fetchone()
        if not invitation or invitation['status']!='PENDING' or invitation['expires_at']<=now():return False
        inviter=membership_role(c,invitation['invited_by'],row['organization_id'])
        if inviter not in (('OWNER',) if invitation['role']=='ADMIN' else ('OWNER','ADMIN')):return False
        from app.billing.access_periods import managed,active
        if managed(c,row['organization_id']) and not active(c,row['organization_id']):return False
        from app.platform.admission import access
        if get_settings().heysow_customer_access_enabled and invitation['invited_by'] not in get_settings().allowed_emails and not access(c,invitation['invited_by']):return False
        return True
    # Billing and optional workspace notifications are authorized by their own
    # immutable payment/access records; no arbitrary message endpoint exists.
    from app.billing.access_periods import notification_authorized
    return notification_authorized(c,row)

def send_provider(payload,key):
    require_enabled();s=get_settings()
    deadline=time.monotonic()+20
    with httpx.Client(timeout=httpx.Timeout(12,connect=4),follow_redirects=False) as client:
        with client.stream('POST','https://api.resend.com/emails',content=json.dumps(payload,separators=(',',':')).encode(),headers={'Authorization':'Bearer '+s.resend_api_key.get_secret_value(),'Content-Type':'application/json','Idempotency-Key':'planebyte-notification/'+key}) as response:
            raw=bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic()>deadline:raise httpx.TimeoutException('Notification exceeded its response deadline.')
                raw.extend(chunk)
                if len(raw)>65536:raise ValueError('Notification response exceeds its bound.')
            if response.status_code in (429,500,502,503,504):raise httpx.TimeoutException('Retryable notification result.')
            if response.status_code not in (200,201,202):raise ValueError('Notification provider rejected the request.')
    result=json.loads(raw)
    if not isinstance(result,dict) or not isinstance(result.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',result['id']):raise ValueError('Invalid notification provider reference.')
    return result['id']

def deliver(key):
    require_enabled();token=str(uuid.uuid4());stamp=int(time.time())
    with db_session() as c:
        security.lock(c,'transactional-delivery')
        row=c.execute('SELECT * FROM transactional_notifications WHERE id=?',(key,)).fetchone()
        if not row or row['status'] not in ('QUEUED','SENDING') or row['available_at']>stamp or row['attempts']>=3 or row['status']=='SENDING' and row['lease_until'] and row['lease_until']>stamp:return
        if row['expires_at']<=stamp or not authorized(c,row):
            c.execute("UPDATE transactional_notifications SET status='CANCELLED',payload_encrypted=NULL,updated_at=? WHERE id=?",(now(),key));return
        active=c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE status='SENDING' AND lease_until>?",(stamp,)).fetchone()[0]
        if active>=2:return
        if security.limited(c,'notification-second','global',1,1):
            c.execute("UPDATE transactional_notifications SET execution_name=NULL,lease_until=NULL,available_at=?,updated_at=? WHERE id=? AND status='QUEUED'",(stamp+2,now(),key));return
        if security.limited(c,'notification-day','global',get_settings().transactional_mail_daily_limit,86400):
            c.execute("UPDATE transactional_notifications SET status='FAILED',error_code='DAILY_DELIVERY_LIMIT',payload_encrypted=NULL,updated_at=? WHERE id=?",(now(),key));return
        c.execute("UPDATE transactional_notifications SET status='SENDING',attempts=attempts+1,lease_token=?,lease_until=?,updated_at=? WHERE id=?",(token,stamp+60,now(),key))
        encrypted=row['payload_encrypted'];attempt=row['attempts']+1
    try:
        payload=json.loads(cipher().decrypt(encrypted.encode()).decode());provider_id=send_provider(payload,key)
    except (httpx.HTTPError,TimeoutError):
        with db_session() as c:c.execute("UPDATE transactional_notifications SET status=?,available_at=?,execution_name=NULL,lease_token=NULL,lease_until=NULL,error_code='DELIVERY_RETRY_PENDING',payload_encrypted=CASE WHEN ?=3 THEN NULL ELSE payload_encrypted END,updated_at=? WHERE id=? AND status='SENDING' AND lease_token=?",('FAILED' if attempt==3 else 'QUEUED',int(time.time())+15,attempt,now(),key,token))
        return
    except Exception:
        with db_session() as c:c.execute("UPDATE transactional_notifications SET status='FAILED',payload_encrypted=NULL,lease_token=NULL,lease_until=NULL,error_code='DELIVERY_PROVIDER_REJECTED',updated_at=? WHERE id=? AND status='SENDING' AND lease_token=?",(now(),key,token))
        return
    with db_session() as c:
        changed=c.execute("UPDATE transactional_notifications SET status='ACCEPTED',provider_message_id=?,payload_encrypted=NULL,lease_token=NULL,lease_until=NULL,error_code=NULL,updated_at=? WHERE id=? AND status='SENDING' AND lease_token=?",(provider_id,now(),key,token)).rowcount
        if changed:
            from app.notifications.webhooks import reconcile
            reconcile(c,key,provider_id)
