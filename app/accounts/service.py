"""Real work-email verification and password recovery over existing identities.

Public endpoints are reachable only through the signed frontend broker. Accounts
remain pending until mailbox control is verified. No implicit domain membership.
"""
import hmac,json,re,secrets,time,uuid
from fastapi import HTTPException
from app.accounts import models,passwords,policy,security,sessions
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.notifications import transactional as mail


def enabled(*,registration=False,invitation=False):
    s=get_settings()
    if not s.heysow_accounts_enabled or not s.heysow_customer_access_enabled:raise HTTPException(503,'Customer account access is not enabled.')
    if registration and not s.heysow_access_periods_enabled:raise HTTPException(503,'Account access enforcement is not enabled.')
    if registration and not (s.heysow_public_registration_enabled or invitation and s.heysow_invited_registration_enabled):raise HTTPException(503,'New account registration is not available.')
    if not s.heysow_terms_version:raise HTTPException(503,'Account terms are awaiting approval.')


def fingerprint(body):
    values=body.model_dump(mode='json')
    values['password']=body.password.get_secret_value()
    values['invitation']=body.invitation_token.get_secret_value() if body.invitation_token else None
    return security.digest('signup-request',json.dumps(values,sort_keys=True,separators=(',',':')))


def ticket(row):
    return {'accepted':True,'challenge_id':row['id'],'capability':security.capability('verify-capability',row['id']+':'+row['email']),'expires_at':row['expires_at']}


def begin_signup(body:models.Signup,client_id):
    enabled(registration=True,invitation=bool(body.invitation_token));mail.require_enabled();s=get_settings()
    invitation_id=None
    if body.invitation_token:
        from app.platform.invitations import pending_for_account
        with db_session() as c:invitation_id=pending_for_account(c,body.email,body.invitation_token.get_secret_value())['id']
    if body.terms_version!=s.heysow_terms_version or body.accepted_terms is not True:raise HTTPException(422,'Accept the current terms before creating your account.')
    security.throttle('signup',body.email,client_id,email_limit=5,client_limit=20)
    digest=fingerprint(body)
    with db_session() as c:
        previous=c.execute('SELECT * FROM account_verifications WHERE email=? AND request_id=?',(body.email,str(body.request_id))).fetchone()
        if previous:
            if previous['request_fingerprint']!=digest:raise HTTPException(409,'Use a new signup request after changing your details.')
            return ticket(previous)
    if not policy.mailbox_domain_available(body.email):raise HTTPException(422,'This company email domain does not accept email. Check the address.')
    # Memory-hard work runs before acquiring any account/database write lock.
    encoded=passwords.hash_password(body.password.get_secret_value())
    stamp=int(time.time());key=str(uuid.uuid4());code=f'{secrets.randbelow(1000000):06d}'
    capability=security.capability('verify-capability',key+':'+body.email)
    with db_session() as c:
        security.lock(c,body.email)
        existing=c.execute('SELECT status FROM customer_accounts WHERE email=?',(body.email,)).fetchone()
        legacy=c.execute('SELECT 1 FROM users WHERE id=?',(body.email,)).fetchone()
        eligible=not(existing or legacy)
        previous=c.execute('SELECT * FROM account_verifications WHERE email=? AND request_id=?',(body.email,str(body.request_id))).fetchone()
        if previous:
            if previous['request_fingerprint']!=digest:raise HTTPException(409,'Use a new signup request after changing your details.')
            return ticket(previous)
        recent=c.execute('SELECT created_at FROM account_verifications WHERE email=? AND invalidated_at IS NULL ORDER BY created_at DESC LIMIT 1',(body.email,)).fetchone()
        if recent and time.time()-__import__('datetime').datetime.fromisoformat(recent['created_at']).timestamp()<60:raise HTTPException(429,'Wait one minute before requesting another verification email.')
        created=now()
        c.execute('UPDATE account_verifications SET invalidated_at=? WHERE email=? AND consumed_at IS NULL AND invalidated_at IS NULL',(created,body.email))
        payload={'eligible':eligible,'password_hash':encoded if eligible else None,'name':body.name,'company_name':body.company_name,'terms_version':body.terms_version,'accepted_at':stamp,'invitation_id':invitation_id}
        c.execute("INSERT INTO account_verifications(id,email,purpose,capability_hash,code_hash,payload_json,request_id,request_fingerprint,expires_at,created_at) VALUES(?,?,'SIGNUP',?,?,?,?,?,?,?)",(key,body.email,security.digest('verify-capability',capability),security.digest('otp',key+':'+code),json.dumps(payload),str(body.request_id),digest,stamp+600,created))
        notification=mail.queue(c,body.email,'SIGNUP_OTP' if eligible else 'SIGNUP_NOTICE',key,{'code':code} if eligible else {},dedupe_key='signup:'+key,expires_at=stamp+600)
        security.audit(c,body.email,'SIGNUP_VERIFICATION_REQUESTED')
    return {'accepted':True,'challenge_id':key,'capability':capability,'expires_at':stamp+600,'notification_id':notification}


def provision_workspace(c,actor,name):
    from app.api.organization import create_organization
    from app.platform.workspaces import select_workspace
    from app.billing.trials import allocate
    # Creating a workspace never joins one merely sharing the same mail domain.
    created=create_organization(c,actor,name);org=created['organization_id']
    c.execute('INSERT INTO customer_workspace_access(organization_id,registered_by,created_at) VALUES(?,?,?) ON CONFLICT(organization_id) DO NOTHING',(org,actor,now()))
    c.execute("UPDATE organization_products SET enabled=1,updated_at=? WHERE organization_id=? AND product='INTENT_RADAR'",(now(),org))
    select_workspace(c,actor,org)
    trial=allocate(c,actor,org)
    return {'organization_id':org,'trial':trial}


def verify_email(body:models.Verify,client_id):
    enabled()
    security.throttle('verify',str(body.challenge_id),client_id,email_limit=10,client_limit=30)
    # Return failures normally, so wrong-code attempts COMMIT instead of being
    # rolled back by a raised HTTPException. Routes choose the public HTTP code.
    with db_session() as c:
        row=c.execute('SELECT * FROM account_verifications WHERE id=?',(str(body.challenge_id),)).fetchone()
        if not row:return {'verified':False,'message':'The code is invalid or expired. Request a new verification email.'}
        security.lock(c,row['email'])
        row=c.execute('SELECT * FROM account_verifications WHERE id=?',(str(body.challenge_id),)).fetchone()
        if not security.matches('verify-capability',body.capability.get_secret_value(),row['capability_hash']):return {'verified':False,'message':'The code is invalid or expired.'}
        if row['consumed_at'] or row['invalidated_at'] or row['expires_at']<=int(time.time()) or row['attempts']>=5:return {'verified':False,'message':'This code is expired or already used. Request a new code, or sign in if you have already verified.'}
        supplied=body.code.get_secret_value()
        valid=bool(re.fullmatch(r'\d{6}',supplied) and security.matches('otp',str(body.challenge_id)+':'+supplied,row['code_hash']))
        if not valid:
            c.execute('UPDATE account_verifications SET attempts=attempts+1,invalidated_at=CASE WHEN attempts>=4 THEN ? ELSE invalidated_at END WHERE id=? AND attempts<5',(now(),row['id']))
            security.audit(c,row['email'],'VERIFICATION_FAILED','DENIED')
            return {'verified':False,'message':'The code is invalid or expired.'}
        payload=json.loads(row['payload_json'])
        if row['purpose']=='SIGNUP':
            enabled(registration=True,invitation=bool(payload.get('invitation_id')))
            if payload.get('invitation_id'):
                from app.platform.invitations import pending_by_id
                pending_by_id(c,row['email'],payload['invitation_id'])
        if payload['terms_version']!=get_settings().heysow_terms_version:return {'verified':False,'message':'The account terms changed. Start a new verification request.'}
        account=c.execute('SELECT * FROM customer_accounts WHERE email=?',(row['email'],)).fetchone()
        if row['purpose']=='SIGNUP' and (not payload.get('eligible') or account or c.execute('SELECT 1 FROM users WHERE id=?',(row['email'],)).fetchone()):return {'verified':False,'message':'Review the sign-in guidance in your email and use your existing sign-in method.'}
        from app.api.organization import ensure_user
        actor=row['email'];ensure_user(c,actor,name=payload['name'])
        created=now()
        if row['purpose']=='SIGNUP':
            c.execute("INSERT INTO customer_accounts(email,user_id,name,company_name,status,password_hash,verified_at,terms_version,terms_accepted_at,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE',?,?,?,?,?,?)",(actor,actor,payload['name'],payload['company_name'],payload['password_hash'],created,payload['terms_version'],payload['accepted_at'],created,created))
        else:
            bound=c.execute("SELECT 1 FROM customer_sessions WHERE id=? AND user_id=? AND provider='GOOGLE' AND revoked_at IS NULL AND expires_at>?",(payload.get('session_id'),actor,int(time.time()))).fetchone()
            if not bound or not account or account['status']!='ACTIVE' or account['password_hash'] or not account['google_subject']:return {'verified':False,'message':'Sign in with Google again before adding a password.'}
            c.execute("UPDATE customer_accounts SET password_hash=?,updated_at=? WHERE user_id=? AND status='ACTIVE' AND password_hash IS NULL",(payload['password_hash'],created,actor))
            c.execute('UPDATE customer_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL',(created,actor))
            security.audit(c,actor,'PASSWORD_LINKED')
        c.execute('UPDATE account_verifications SET consumed_at=? WHERE id=? AND consumed_at IS NULL',(created,row['id']))
        c.execute("UPDATE transactional_notifications SET status='CANCELLED',payload_encrypted=NULL,updated_at=? WHERE authority_id=? AND purpose IN ('SIGNUP_OTP','SET_PASSWORD_OTP') AND status='QUEUED'",(created,row['id']))
        c.execute('INSERT INTO account_terms_acceptances(nonce,user_id,terms_version,accepted_at,recorded_at) VALUES(?,?,?,?,?)',(row['id'],actor,payload['terms_version'],str(payload['accepted_at']),created))
        workspace=provision_workspace(c,actor,payload['company_name']) if row['purpose']=='SIGNUP' and not payload.get('invitation_id') else {}
        security.audit(c,actor,'EMAIL_VERIFIED')
        return {'verified':True,'login_ticket':sessions.exchange_ticket(c,actor),**workspace}


def login(body:models.Login,client_id):
    enabled();security.throttle('login',body.email,client_id,email_limit=10,client_limit=30,seconds=900)
    with db_session() as c:row=c.execute('SELECT * FROM customer_accounts WHERE email=?',(body.email,)).fetchone()
    valid=passwords.verify(body.password.get_secret_value(),row['password_hash'] if row and row['status']=='ACTIVE' and row['verified_at'] else None)
    if not valid:
        with db_session() as c:security.audit(c,body.email,'PASSWORD_LOGIN','DENIED')
        return {'authenticated':False,'message':'Email or password is incorrect, or verification is incomplete.'}
    with db_session() as c:
        security.lock(c,body.email)
        current=c.execute('SELECT * FROM customer_accounts WHERE email=?',(body.email,)).fetchone()
        if not current or current['status']!='ACTIVE' or current['password_hash']!=row['password_hash']:return {'authenticated':False,'message':'Sign in again with your verified account.'}
        security.audit(c,body.email,'PASSWORD_LOGIN')
        return {'authenticated':True,'email':body.email,'name':row['name'],'admitted':True,'requires_terms':row['terms_version']!=get_settings().heysow_terms_version,**sessions.create(c,body.email,'PASSWORD')}


def recover(body:models.Recovery,client_id):
    enabled();mail.require_enabled();security.throttle('recovery',body.email,client_id,email_limit=3,client_limit=15)
    # Identical public work for existing, Google-only and unknown accounts. The
    # account lookup and eligible email happen only after the response is queued.
    email_hash=security.digest('recovery-address',body.email)
    with db_session() as c:
        security.lock(c,body.email)
        previous=c.execute('SELECT id FROM account_recovery_requests WHERE email_hash=? AND request_id=?',(email_hash,str(body.request_id))).fetchone()
        if previous:return {'accepted':True,'recovery_request_id':previous[0]}
        key=str(uuid.uuid4())
        c.execute("INSERT INTO account_recovery_requests(id,email,email_hash,request_id,status,expires_at,created_at) VALUES(?,?,?,?,'QUEUED',?,?)",(key,body.email,email_hash,str(body.request_id),int(time.time())+1200,now()))
    return {'accepted':True,'recovery_request_id':key}


def prepare_recovery(key):
    enabled();mail.require_enabled()
    with db_session() as c:
        security.lock(c,'recovery:'+key)
        request=c.execute('SELECT * FROM account_recovery_requests WHERE id=?',(key,)).fetchone()
        if not request or request['status']!='QUEUED':return None
        if request['expires_at']<=int(time.time()):
            c.execute("UPDATE account_recovery_requests SET status='EXPIRED',email=NULL,processed_at=? WHERE id=?",(now(),key));return None
        email=request['email']
        row=c.execute("SELECT user_id FROM customer_accounts WHERE email=? AND status='ACTIVE' AND verified_at IS NOT NULL AND password_hash IS NOT NULL",(email,)).fetchone()
        notification=None
        if row:
            token=security.capability('reset-token',key)
            c.execute('INSERT INTO account_recovery_tokens(id,user_id,token_hash,request_id,expires_at,created_at) VALUES(?,?,?,?,?,?)',(key,row['user_id'],security.digest('reset-token',token),request['request_id'],request['expires_at'],now()))
            notification=mail.queue(c,email,'PASSWORD_RESET',key,{'token':token},dedupe_key='password-reset:'+key,expires_at=request['expires_at'])
            security.audit(c,email,'PASSWORD_RECOVERY_REQUESTED')
        c.execute("UPDATE account_recovery_requests SET status='PROCESSED',email=NULL,processed_at=? WHERE id=?",(now(),key))
        return notification


def reset_password(body:models.Reset,client_id):
    enabled();mail.require_enabled();security.throttle('reset','opaque-token',client_id,email_limit=30,client_limit=15)
    encoded=passwords.hash_password(body.password.get_secret_value())
    with db_session() as c:
        row=c.execute('SELECT * FROM account_recovery_tokens WHERE token_hash=?',(security.digest('reset-token',body.token.get_secret_value()),)).fetchone()
        if not row:return {'reset':False,'message':'The reset link is invalid or expired.'}
        security.lock(c,row['user_id'])
        current=c.execute('SELECT * FROM account_recovery_tokens WHERE id=?',(row['id'],)).fetchone()
        if current['consumed_at'] or current['expires_at']<=int(time.time()):return {'reset':False,'message':'The reset link is invalid or expired.'}
        account=c.execute("SELECT email FROM customer_accounts WHERE user_id=? AND status='ACTIVE' AND password_hash IS NOT NULL",(row['user_id'],)).fetchone()
        if not account:return {'reset':False,'message':'The reset link is invalid or expired.'}
        stamp=now();actor=row['user_id']
        c.execute('UPDATE customer_accounts SET password_hash=?,updated_at=? WHERE user_id=?',(encoded,stamp,actor))
        c.execute('UPDATE account_recovery_tokens SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL',(stamp,actor))
        c.execute('UPDATE customer_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL',(stamp,actor))
        c.execute('UPDATE account_login_tickets SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL',(stamp,actor))
        security.audit(c,actor,'PASSWORD_CHANGED')
        mail.queue(c,account['email'],'PASSWORD_CHANGED',row['id'],{},dedupe_key='password-changed:'+row['id'],expires_at=int(time.time())+86400)
    return {'reset':True,'message':'Password changed. Sign in again with your new password.'}


def resend_verification(body:models.Resend,client_id):
    enabled();mail.require_enabled()
    with db_session() as c:old=c.execute('SELECT * FROM account_verifications WHERE id=?',(str(body.challenge_id),)).fetchone()
    if not old or not security.matches('verify-capability',body.capability.get_secret_value(),old['capability_hash']):raise HTTPException(400,'Start a new verification request.')
    security.throttle('signup',old['email'],client_id,email_limit=5,client_limit=20)
    with db_session() as c:
        security.lock(c,old['email'])
        prior=c.execute('SELECT * FROM account_verifications WHERE email=? AND request_id=?',(old['email'],str(body.request_id))).fetchone()
        if prior:return ticket(prior)
        current=c.execute('SELECT * FROM account_verifications WHERE id=?',(old['id'],)).fetchone()
        if current['consumed_at'] or time.time()-__import__('datetime').datetime.fromisoformat(current['created_at']).timestamp()>86400:raise HTTPException(400,'Start a new verification request or sign in with your verified account.')
        latest=c.execute('SELECT created_at FROM account_verifications WHERE email=? ORDER BY created_at DESC LIMIT 1',(old['email'],)).fetchone()
        if time.time()-__import__('datetime').datetime.fromisoformat(latest['created_at']).timestamp()<60:raise HTTPException(429,'Wait one minute before requesting another verification email.')
        key=str(uuid.uuid4());cap=security.capability('verify-capability',key+':'+old['email']);code=f'{secrets.randbelow(1000000):06d}';stamp=int(time.time());created=now()
        c.execute('UPDATE account_verifications SET invalidated_at=? WHERE email=? AND consumed_at IS NULL AND invalidated_at IS NULL',(created,old['email']))
        c.execute('INSERT INTO account_verifications(id,email,purpose,capability_hash,code_hash,payload_json,request_id,request_fingerprint,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(key,old['email'],old['purpose'],security.digest('verify-capability',cap),security.digest('otp',key+':'+code),old['payload_json'],str(body.request_id),old['request_fingerprint'],stamp+600,created))
        payload=json.loads(old['payload_json']);eligible=payload.get('eligible',True)
        purpose=('SIGNUP_OTP' if eligible else 'SIGNUP_NOTICE') if old['purpose']=='SIGNUP' else 'SET_PASSWORD_OTP'
        notification=mail.queue(c,old['email'],purpose,key,{'code':code} if eligible else {},dedupe_key='verification:'+key,expires_at=stamp+600)
        return {'accepted':True,'challenge_id':key,'capability':cap,'expires_at':stamp+600,'notification_id':notification}


def start_password(c,actor,token,body):
    enabled();mail.require_enabled();state=sessions.validate(c,actor,token)
    if state['provider']!='GOOGLE':raise HTTPException(403,'Sign in with Google before adding a password.')
    account=c.execute("SELECT * FROM customer_accounts WHERE user_id=? AND status='ACTIVE'",(actor,)).fetchone()
    if not account or not account['google_subject'] or account['password_hash']:raise HTTPException(409,'Use password recovery to change an existing password.')
    digest=security.digest('set-password-request',body.password.get_secret_value())
    previous=c.execute('SELECT * FROM account_verifications WHERE email=? AND request_id=?',(actor,str(body.request_id))).fetchone()
    if previous:
        if previous['purpose']!='SET_PASSWORD' or previous['request_fingerprint']!=digest:raise HTTPException(409,'Use a new request after changing your password.')
        return ticket(previous)
    encoded=passwords.hash_password(body.password.get_secret_value());key=str(uuid.uuid4());stamp=int(time.time());code=f'{secrets.randbelow(1000000):06d}'
    cap=security.capability('verify-capability',key+':'+actor);created=now()
    payload={'password_hash':encoded,'session_id':state['id'],'name':account['name'],'company_name':account['company_name'],'terms_version':account['terms_version'],'accepted_at':account['terms_accepted_at']}
    security.lock(c,actor)
    c.execute("UPDATE account_verifications SET invalidated_at=? WHERE email=? AND purpose='SET_PASSWORD' AND consumed_at IS NULL AND invalidated_at IS NULL",(created,actor))
    c.execute("INSERT INTO account_verifications(id,email,purpose,capability_hash,code_hash,payload_json,request_id,request_fingerprint,expires_at,created_at) VALUES(?,?,'SET_PASSWORD',?,?,?,?,?,?,?)",(key,actor,security.digest('verify-capability',cap),security.digest('otp',key+':'+code),json.dumps(payload),str(body.request_id),digest,stamp+600,created))
    mail.queue(c,actor,'SET_PASSWORD_OTP',key,{'code':code},dedupe_key='set-password:'+key,expires_at=stamp+600)
    return ticket(c.execute('SELECT * FROM account_verifications WHERE id=?',(key,)).fetchone())

def accept_terms(c,actor,token,body):
    enabled();sessions.validate(c,actor,token,require_current_terms=False)
    if body.accepted is not True or body.terms_version!=get_settings().heysow_terms_version:raise HTTPException(422,'Accept the current account terms to continue.')
    security.lock(c,actor);nonce=str(body.request_id);stamp=now()
    prior=c.execute('SELECT user_id,terms_version FROM account_terms_acceptances WHERE nonce=?',(nonce,)).fetchone()
    if prior and (prior['user_id']!=actor or prior['terms_version']!=body.terms_version):raise HTTPException(409,'Use a new consent request.')
    c.execute('INSERT INTO account_terms_acceptances(nonce,user_id,terms_version,accepted_at,recorded_at) VALUES(?,?,?,?,?) ON CONFLICT(nonce) DO NOTHING',(nonce,actor,body.terms_version,str(int(time.time())),stamp))
    c.execute('UPDATE customer_accounts SET terms_version=?,terms_accepted_at=?,updated_at=? WHERE user_id=?',(body.terms_version,int(time.time()),stamp,actor))
    security.audit(c,actor,'ACCOUNT_TERMS_ACCEPTED')
    return {'accepted':True,'terms_version':body.terms_version}
