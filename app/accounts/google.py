"""Real Google-broker admission and explicit credential linking; no email auto-merge."""
import time,uuid
from fastapi import HTTPException
from app.accounts import policy,security,sessions
from app.config.settings import get_settings
from app.database.prospects import now


def _consent(c,body,existing):
    s=get_settings()
    if existing and existing['terms_version']==s.heysow_terms_version and body.acceptance_nonce is None:return
    if body.terms_version!=s.heysow_terms_version or body.accepted_at is None or not body.acceptance_nonce or not 0<=int(time.time())-body.accepted_at<=600:
        raise HTTPException(422,'Accept the current terms before creating or updating your account.')
    prior=c.execute('SELECT user_id,terms_version FROM account_terms_acceptances WHERE nonce=?',(body.acceptance_nonce,)).fetchone()
    if prior and (prior['user_id']!=body.email or prior['terms_version']!=s.heysow_terms_version):raise HTTPException(409,'Consent has already been used.')


def admit(c,body):
    # The existing admission entrypoint already verifies broker authentication,
    # email_verified, actor equality, Google client ID and configured terms.
    s=get_settings();email=body.email;security.lock(c,email)
    account=c.execute('SELECT * FROM customer_accounts WHERE email=?',(email,)).fetchone()
    legacy=c.execute('SELECT * FROM account_admissions WHERE user_id=?',(email,)).fetchone()
    if account and account['status']!='ACTIVE' or legacy and legacy['status']!='ACTIVE':raise HTTPException(403,'Account access requires administrator review.')
    subject=c.execute('SELECT email FROM customer_accounts WHERE google_subject=?',(body.google_subject,)).fetchone()
    legacy_subject=c.execute('SELECT user_id FROM account_admissions WHERE google_subject=?',(body.google_subject,)).fetchone()
    if subject and subject['email']!=email or legacy_subject and legacy_subject['user_id']!=email:raise HTTPException(403,'This verified Google identity belongs to a different account.')
    if account and account['google_subject'] not in (None,body.google_subject) or legacy and legacy['google_subject']!=body.google_subject:raise HTTPException(403,'Google identity does not match the account.')
    if account and account['password_hash'] and not account['google_subject']:
        link=body.link_token.get_secret_value() if body.link_token else ''
        ticket=c.execute('SELECT * FROM account_link_tickets WHERE token_hash=?',(security.digest('google-link',link),)).fetchone() if link else None
        if not ticket or ticket['user_id']!=email or ticket['consumed_at'] or ticket['expires_at']<=int(time.time()):raise HTTPException(409,'Sign in with your password and explicitly link Google from Account settings.')
        active=c.execute('SELECT 1 FROM customer_sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>?',(ticket['session_id'],email,int(time.time()))).fetchone()
        if not active:raise HTTPException(401,'Sign in again before linking Google.')
        c.execute('UPDATE account_link_tickets SET consumed_at=? WHERE id=? AND consumed_at IS NULL',(now(),ticket['id']))
        security.audit(c,email,'GOOGLE_LINKED')
    existing=account or legacy
    if not existing:
        try:policy.work_email(email)
        except ValueError:raise HTTPException(422,policy.MESSAGE) from None
        if not s.heysow_public_registration_enabled:
            if not s.heysow_invited_registration_enabled or not body.invitation_token:raise HTTPException(403,'New account registration is not available.')
    if body.invitation_token:
        from app.platform.invitations import pending_for_account
        pending_for_account(c,email,body.invitation_token)
    _consent(c,body,existing)
    if not existing and c.execute('SELECT 1 FROM users WHERE id=?',(email,)).fetchone():raise HTTPException(409,'Use the existing sign-in method. Linking requires an authenticated account request.')
    from app.api.organization import ensure_user
    ensure_user(c,email,name=body.name or None)
    stamp=now();terms=s.heysow_terms_version
    company=policy.company_domain(email).split('.')[0].capitalize()+' workspace' if not existing else account['company_name'] if account else 'Your workspace'
    if not account:
        c.execute("INSERT INTO customer_accounts(email,user_id,name,company_name,status,google_subject,verified_at,terms_version,terms_accepted_at,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE',?,?,?,?,?,?)",(email,email,body.name or email.split('@')[0],company,body.google_subject,stamp,terms,body.accepted_at or int(time.time()),stamp,stamp))
    else:c.execute('UPDATE customer_accounts SET google_subject=?,terms_version=?,terms_accepted_at=COALESCE(?,terms_accepted_at),updated_at=? WHERE email=?',(body.google_subject,terms,body.accepted_at,stamp,email))
    c.execute("INSERT INTO account_admissions(user_id,google_subject,status,terms_version,created_at,updated_at) VALUES(?,?,'ACTIVE',?,?,?) ON CONFLICT(user_id) DO UPDATE SET terms_version=excluded.terms_version,updated_at=excluded.updated_at",(email,body.google_subject,terms,stamp,stamp))
    if body.acceptance_nonce:
        c.execute('INSERT INTO account_terms_acceptances(nonce,user_id,terms_version,accepted_at,recorded_at) VALUES(?,?,?,?,?) ON CONFLICT(nonce) DO NOTHING',(body.acceptance_nonce,email,terms,str(body.accepted_at),stamp))
        security.audit(c,email,'ACCOUNT_TERMS_ACCEPTED')
    workspace={}
    if not existing and not body.invitation_token:
        from app.accounts.service import provision_workspace
        workspace=provision_workspace(c,email,company)
    security.audit(c,email,'GOOGLE_LOGIN')
    return {'user_id':email,'status':'ACTIVE','existing':bool(existing),'terms_version':terms,'workspace_required':False,**workspace,**sessions.create(c,email,'GOOGLE')}


def begin_link(c,actor,token):
    state=sessions.validate(c,actor,token)
    key=str(uuid.uuid4());value=security.capability('google-link-ticket',key)
    c.execute('INSERT INTO account_link_tickets(id,user_id,session_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?,?)',(key,actor,state['id'],security.digest('google-link',value),int(time.time())+600,now()))
    return {'link_token':value,'expires_at':int(time.time())+600}
