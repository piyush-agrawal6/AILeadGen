"""DNS ownership proof, separate from public website evidence and membership."""
import asyncio
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime,timedelta,timezone
from pydantic import BaseModel,ConfigDict,Field,field_validator
from fastapi import HTTPException
from app.platform.context import organization,current
from app.api.organization import require_role,membership_role
from app.database.prospects import now

PREFIX='heysow-verification='

class DomainCreate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    domain:str=Field(min_length=3,max_length=253)

    @field_validator('domain')
    @classmethod
    def normalize(cls,value):
        import re
        from app.utils.urls import _tld_extractor
        if '://' in value or '/' in value or ':' in value or '@' in value:raise ValueError('Enter a public domain name, without a URL path or port.')
        try:value=value.rstrip('.').encode('idna').decode('ascii').lower()
        except UnicodeError:raise ValueError('Enter a valid domain name.') from None
        if not _tld_extractor(value).suffix or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in value.split('.')):raise ValueError('Enter a registrable public domain name.')
        extracted=_tld_extractor(value)
        if not extracted.domain:raise ValueError('A public suffix alone cannot be verified.')
        if len('_heysow-verify.'+value)>253:raise ValueError('This domain is too long for a verification record.')
        return value

def _manager(c):
    org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'))
    return org

def _lock(c,org):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    _manager(c)

def _owned(c,key):
    row=c.execute('SELECT * FROM organization_domains WHERE id=? AND organization_id=?',(key,organization())).fetchone()
    if not row:raise HTTPException(404,'Domain not found.')
    return dict(row)

def _audit(c,key,action):
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),current().actor,action,'domain:'+key,'SUCCESS',organization(),now()))

def listing(c):
    org=organization()
    rows=c.execute('SELECT id,domain,status,challenge_expires_at,verified_at,checked_at FROM organization_domains WHERE organization_id=? ORDER BY domain LIMIT 100',(org,)).fetchall()
    return {'items':[{**dict(row),'status':'EXPIRED' if row['status']=='PENDING' and row['challenge_expires_at']<=now() else row['status']} for row in rows],'can_edit':membership_role(c,current().actor,org) in ('OWNER','ADMIN')}

def challenge(c,body:DomainCreate):
    org=_manager(c);_lock(c,org)
    existing=c.execute('SELECT * FROM organization_domains WHERE organization_id=? AND domain=?',(org,body.domain)).fetchone()
    if existing and existing['status']=='VERIFIED':raise HTTPException(409,'This domain already has recorded ownership verification.')
    if existing and datetime.now(timezone.utc)-datetime.fromisoformat(existing['updated_at'])<timedelta(seconds=30):raise HTTPException(429,'Wait 30 seconds before replacing this challenge.')
    from app.config.settings import get_settings
    if not existing and c.execute('SELECT COUNT(*) FROM organization_domains WHERE organization_id=?',(org,)).fetchone()[0]>=get_settings().heysow_domain_limit:raise HTTPException(409,'This workspace has reached its domain verification safety limit.')
    token=secrets.token_urlsafe(32);digest=hashlib.sha256((PREFIX+token).encode()).hexdigest();stamp=now();key=existing['id'] if existing else str(uuid.uuid4())
    expiry=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
    c.execute('''INSERT INTO organization_domains(id,organization_id,domain,status,challenge_hash,challenge_expires_at,created_at,updated_at)
        VALUES(?,?,?,'PENDING',?,?,?,?) ON CONFLICT(organization_id,domain) DO UPDATE SET status='PENDING',challenge_hash=excluded.challenge_hash,
        challenge_expires_at=excluded.challenge_expires_at,updated_at=excluded.updated_at,attempts=0,checked_at=NULL''',(key,org,body.domain,digest,expiry,stamp,stamp))
    _audit(c,key,'DOMAIN_CHALLENGE_CREATED')
    return {'id':key,'domain':body.domain,'record_type':'TXT','record_name':'_heysow-verify.'+body.domain,'record_value':PREFIX+token,'expires_at':expiry}

def _resolve(name):
    import dns.resolver
    resolver=dns.resolver.Resolver();resolver.timeout=2;resolver.lifetime=5
    try:
        result=resolver.resolve(name,'TXT',lifetime=5,search=False)
        return [b''.join(record.strings).decode('utf-8',errors='replace')[:1024] for record in list(result)[:20]]
    except (dns.resolver.NXDOMAIN,dns.resolver.NoAnswer):return []

async def verify(c,key):
    _manager(c);row=_owned(c,key)
    if row['status']=='VERIFIED':return {'status':'VERIFIED','verified_at':row['verified_at']}
    if row['status']!='PENDING' or row['challenge_expires_at']<=now():raise HTTPException(409,'Create a new domain verification challenge.')
    if row['checked_at'] and datetime.now(timezone.utc)-datetime.fromisoformat(row['checked_at'])<timedelta(seconds=30):raise HTTPException(429,'Wait 30 seconds before checking DNS again.')
    if row['attempts']>=20:raise HTTPException(429,'This challenge has reached its check limit. Create a new challenge after reviewing DNS.')
    # Reserve a check before external I/O so concurrent requests cannot all pass
    # the same cooldown. This commits only this deliberate attempt record.
    stamp=now();cutoff=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()
    changed=c.execute("UPDATE organization_domains SET checked_at=?,attempts=attempts+1 WHERE id=? AND organization_id=? AND status='PENDING' AND challenge_hash=? AND attempts<20 AND (checked_at IS NULL OR checked_at<=?)",(stamp,key,organization(),row['challenge_hash'],cutoff)).rowcount
    if changed!=1:raise HTTPException(429,'A verification check is already in progress. Retry later.')
    c.commit()
    try:records=await asyncio.wait_for(asyncio.to_thread(_resolve,'_heysow-verify.'+row['domain']),timeout=7)
    except Exception:raise HTTPException(503,'DNS could not be checked. Retry later; ownership has not been verified.') from None
    org=_manager(c);_lock(c,org);latest=_owned(c,key)
    if latest['challenge_hash']!=row['challenge_hash'] or latest['status']!='PENDING' or latest['challenge_expires_at']<=now():raise HTTPException(409,'The domain challenge changed. Reload it before verifying.')
    matched=any(hmac.compare_digest(hashlib.sha256(record.encode()).hexdigest(),row['challenge_hash']) for record in records)
    stamp=now()
    c.execute('UPDATE organization_domains SET checked_at=?,status=?,verified_at=?,updated_at=? WHERE id=? AND organization_id=?',
        (stamp,'VERIFIED' if matched else 'PENDING',stamp if matched else latest['verified_at'],stamp,key,org))
    if matched:_audit(c,key,'DOMAIN_OWNERSHIP_VERIFIED')
    return {'status':'VERIFIED' if matched else 'PENDING','verified_at':stamp if matched else None}

def revoke(c,key):
    org=_manager(c);_lock(c,org);_owned(c,key)
    c.execute("UPDATE organization_domains SET status='REVOKED',updated_at=? WHERE id=? AND organization_id=?",(now(),key,org))
    _audit(c,key,'DOMAIN_VERIFICATION_REVOKED')
    return {'status':'REVOKED'}
