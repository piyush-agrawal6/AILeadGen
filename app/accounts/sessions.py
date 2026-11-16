"""Opaque server-side sessions and one-use post-verification exchanges."""
import secrets,time,uuid
from fastapi import HTTPException
from app.accounts import security
from app.database.prospects import now


def create(c,actor,provider):
    key=str(uuid.uuid4());token=secrets.token_urlsafe(32);stamp=int(time.time())
    c.execute('INSERT INTO customer_sessions(id,user_id,token_hash,provider,created_at,expires_at) VALUES(?,?,?,?,?,?)',(key,actor,security.digest('session',token),provider,now(),stamp+8*3600))
    # Bounded active-session count; historical records remain intact.
    rows=c.execute('SELECT id FROM customer_sessions WHERE user_id=? AND revoked_at IS NULL AND expires_at>? ORDER BY created_at DESC,id DESC',(actor,stamp)).fetchall()
    for row in rows[20:]:c.execute('UPDATE customer_sessions SET revoked_at=? WHERE id=? AND user_id=? AND revoked_at IS NULL',(now(),row['id'],actor))
    return {'user_id':actor,'session_token':token,'expires_at':stamp+8*3600}

def validate(c,actor,token,*,require_current_terms=True):
    from app.config.settings import get_settings
    if not isinstance(token,str) or not 40<=len(token)<=100:raise HTTPException(401,'Sign in again to continue.')
    row=c.execute("SELECT s.*,a.email,a.name,a.terms_version FROM customer_sessions s JOIN customer_accounts a ON a.user_id=s.user_id WHERE s.user_id=? AND s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND a.status='ACTIVE' AND a.verified_at IS NOT NULL",(actor,security.digest('session',token),int(time.time()))).fetchone()
    if not row:raise HTTPException(401,'Sign in again to continue.')
    if require_current_terms and row['terms_version']!=get_settings().heysow_terms_version:raise HTTPException(403,{'code':'TERMS_REQUIRED','message':'Review and accept the current account terms to continue.'})
    return dict(row)

def revoke(c,actor,token):
    c.execute('UPDATE customer_sessions SET revoked_at=? WHERE user_id=? AND token_hash=? AND revoked_at IS NULL',(now(),actor,security.digest('session',token)))
    return {'signed_out':True}

def exchange_ticket(c,actor):
    key=str(uuid.uuid4());token=secrets.token_urlsafe(32)
    c.execute('INSERT INTO account_login_tickets(id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)',(key,actor,security.digest('exchange',token),int(time.time())+120,now()))
    return token

def exchange(c,token):
    digest=security.digest('exchange',token)
    row=c.execute('SELECT * FROM account_login_tickets WHERE token_hash=?',(digest,)).fetchone()
    if not row:raise HTTPException(401,'Sign in with your verified account to continue.')
    security.lock(c,row['user_id'])
    changed=c.execute('UPDATE account_login_tickets SET consumed_at=? WHERE id=? AND consumed_at IS NULL AND expires_at>?',(now(),row['id'],int(time.time()))).rowcount
    if changed!=1:raise HTTPException(401,'This sign-in exchange has expired or was already used.')
    account=c.execute("SELECT name FROM customer_accounts WHERE user_id=? AND status='ACTIVE' AND verified_at IS NOT NULL",(row['user_id'],)).fetchone()
    if not account:raise HTTPException(401,'Sign in with your verified account to continue.')
    return {**create(c,row['user_id'],'PASSWORD'),'name':account['name'],'email':row['user_id'],'admitted':True}
