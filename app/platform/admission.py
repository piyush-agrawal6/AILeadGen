"""Verified Google broker admission, gated independently of workspace ownership."""
import time
from uuid import UUID,uuid4
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator,SecretStr
from app.config.settings import get_settings
from app.api.organization import ensure_user
from app.database.prospects import now

PATH='/api/organization/admission/google'


class GoogleAdmission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    email:str=Field(min_length=3,max_length=254)
    google_subject:str=Field(min_length=1,max_length=255)
    client_id:str=Field(min_length=1,max_length=300)
    email_verified:bool
    link_token:SecretStr|None=Field(None,repr=False,exclude=True)
    name:str=Field('',max_length=120)
    terms_version:str=Field('',max_length=100)
    accepted_at:int|None=None
    acceptance_nonce:str|None=Field(None,max_length=36)
    invitation_token:str|None=Field(None,min_length=40,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('email')
    @classmethod
    def identity(cls,value):
        from app.mail.contacted import normalize
        if normalize(value)!=value or value!=value.lower():raise ValueError('A normalized verified email is required.')
        return value

    @field_validator('acceptance_nonce')
    @classmethod
    def nonce(cls,value):
        if value is not None and str(UUID(value))!=value:raise ValueError('Invalid consent nonce.')
        return value


def is_bootstrap(path,method):
    s=get_settings()
    return path==PATH and method=='POST' and s.heysow_customer_access_enabled and (s.heysow_public_registration_enabled or s.heysow_invited_registration_enabled or bool(s.heysow_registration_acceptance_emails.strip()))


def access(c,actor,*,require_terms=True):
    from app.accounts.policy import require_work_identity
    try:require_work_identity(actor)
    except HTTPException:return False
    s=get_settings()
    if not s.heysow_customer_access_enabled or not s.heysow_terms_version:return False
    if s.heysow_accounts_enabled:
        customer=c.execute('SELECT status,terms_version,verified_at FROM customer_accounts WHERE user_id=?',(actor,)).fetchone()
        if customer:return bool(customer['status']=='ACTIVE' and customer['verified_at'] and (not require_terms or customer['terms_version']==s.heysow_terms_version))
    row=c.execute('SELECT status,terms_version FROM account_admissions WHERE user_id=?',(actor,)).fetchone()
    return bool(row and row['status']=='ACTIVE' and (not require_terms or row['terms_version']==s.heysow_terms_version))


def admit(c,body,*,actor,broker_verified):
    s=get_settings()
    if not broker_verified:raise HTTPException(401,'Verified server authentication is required.')
    from app.accounts.policy import require_work_identity
    require_work_identity(actor)
    if not s.heysow_customer_access_enabled:raise HTTPException(503,'Customer account access is not enabled.')
    if actor!=body.email or not body.email_verified or not s.heysow_google_admission_client_id or body.client_id!=s.heysow_google_admission_client_id:
        raise HTTPException(403,'Verified Google account identity is required.')
    terms=s.heysow_terms_version
    if not terms:raise HTTPException(503,'Account terms are awaiting approval.')
    if s.heysow_accounts_enabled:
        from app.accounts.google import admit as customer_admit
        return customer_admit(c,body)
    # Short, provider-free transaction serializes identity/consent races. Unique
    # user and subject constraints independently prevent cross-account adoption.
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944529)')
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    row=c.execute('SELECT * FROM account_admissions WHERE user_id=? OR google_subject=?',(actor,body.google_subject)).fetchall()
    if row and (len(row)!=1 or row[0]['user_id']!=actor or row[0]['google_subject']!=body.google_subject or row[0]['status']!='ACTIVE'):
        raise HTTPException(403,'Account access requires administrator review.')
    existing=bool(row)
    if existing and row[0]['terms_version']==terms and body.acceptance_nonce is None:
        return {'user_id':actor,'status':'ACTIVE','existing':True,'terms_version':terms,'workspace_required':True}
    if not existing and not s.heysow_public_registration_enabled:
        if not s.heysow_invited_registration_enabled or not body.invitation_token:
            raise HTTPException(403,'Public registration is not enabled.')
        from app.platform.invitations import pending_for_account
        pending_for_account(c,actor,body.invitation_token)
    if body.terms_version!=terms or body.accepted_at is None or not body.acceptance_nonce or not 0<=int(time.time())-body.accepted_at<=600:
        raise HTTPException(422,'Accept the current terms before creating or updating your account.')
    consent=c.execute('SELECT user_id,terms_version FROM account_terms_acceptances WHERE nonce=?',(body.acceptance_nonce,)).fetchone()
    if consent and (consent['user_id']!=actor or consent['terms_version']!=terms):raise HTTPException(409,'Consent has already been used.')
    ensure_user(c,actor,name=body.name or None)
    stamp=now()
    c.execute("INSERT INTO account_admissions(user_id,google_subject,status,terms_version,created_at,updated_at) VALUES(?,?,'ACTIVE',?,?,?) ON CONFLICT(user_id) DO UPDATE SET terms_version=excluded.terms_version,updated_at=excluded.updated_at",(actor,body.google_subject,terms,stamp,stamp))
    c.execute('INSERT INTO account_terms_acceptances(nonce,user_id,terms_version,accepted_at,recorded_at) VALUES(?,?,?,?,?) ON CONFLICT(nonce) DO NOTHING',(body.acceptance_nonce,actor,terms,str(body.accepted_at),stamp))
    if not consent:
        c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid4()),actor,'ACCOUNT_TERMS_ACCEPTED','account:'+actor,'SUCCESS','{}',stamp))
    return {'user_id':actor,'status':'ACTIVE','existing':existing,'terms_version':terms,'workspace_required':True}
