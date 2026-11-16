"""Account-scoped cryptography, committed abuse counters and safe audit events."""
import base64,hashlib,hmac,json,time,uuid
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now

def signing_key():
    key=get_settings().api_signing_secret
    if len(key)<32:raise HTTPException(503,'Account security is not configured.')
    return key.encode()

def digest(purpose,value):
    return hmac.new(signing_key(),('planebyte:accounts:v1:'+purpose+':'+value).encode(),hashlib.sha256).hexdigest()

def capability(purpose,identifier):
    return base64.urlsafe_b64encode(bytes.fromhex(digest(purpose,identifier))).decode().rstrip('=')

def matches(purpose,value,expected):
    return isinstance(value,str) and isinstance(expected,str) and hmac.compare_digest(digest(purpose,value),expected)

def lock(c,email):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,691948001))',(email,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')

def audit(c,email,action,result='SUCCESS'):
    c.execute('INSERT INTO account_security_events(id,account_hash,action,result,created_at) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),digest('audit',email),action,result,now()))

def limited(c,kind,value,limit,seconds,stamp=None):
    stamp=int(time.time()) if stamp is None else stamp;window=stamp//seconds*seconds
    row=c.execute('INSERT INTO account_rate_limits(kind,bucket_hash,window_start,used) VALUES(?,?,?,1) ON CONFLICT(kind,bucket_hash,window_start) DO UPDATE SET used=account_rate_limits.used+1 RETURNING used',(kind,digest('rate',value),window)).fetchone()
    return row[0]>limit

def throttle(kind,email,client_id,*,email_limit=5,client_limit=20,seconds=3600):
    # Commit attempts even when the request is later rejected or rolls back.
    # Client identity is a signed broker-provided hash, not a browser authority.
    with db_session() as c:
        lock(c,'global-account-rate')
        blocked=limited(c,kind+':email',email,email_limit,seconds)
        blocked=limited(c,kind+':client',client_id,client_limit,seconds) or blocked
        blocked=limited(c,kind+':global','global',200,seconds) or blocked
        if blocked:audit(c,email,'RATE_LIMITED','DENIED')
    if blocked:raise HTTPException(429,'Too many account requests. Retry later.')
