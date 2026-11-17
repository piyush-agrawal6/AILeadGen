"""Scoped privacy intake and a bounded personal account export.

Requests do not delete a workspace, change paid access or erase history. Closure
verification and retention exceptions require an operator's scoped review.
"""
import time,uuid,re
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict
from fastapi import HTTPException
from app.accounts import security,sessions
from app.database.prospects import now

POLICY='2026-11-16.owner-proposed-retention.1'
class PrivacyRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['EXPORT','CLOSE_AND_DELETE','ERASURE']
    request_id:UUID
    confirmed:Literal[True]

def account_export(c,actor,token):
    sessions.validate(c,actor,token)
    row=c.execute('SELECT email,name,company_name,status,verified_at,terms_version,created_at FROM customer_accounts WHERE user_id=?',(actor,)).fetchone()
    memberships=[dict(r) for r in c.execute('SELECT organization_id,role,status,created_at FROM organization_memberships WHERE user_id=? ORDER BY organization_id LIMIT 100',(actor,)).fetchall()]
    profile=c.execute('SELECT display_name,job_title,timezone,locale,created_at,updated_at FROM user_profiles WHERE user_id=?',(actor,)).fetchone()
    return {'document':'PlaneByte personal account export','generated_at':now(),'account':dict(row),'profile':dict(profile) if profile else {},'memberships':memberships,'scope':'Account details and up to 100 memberships. Export saved research using the relevant workspace export, or request a full data export for operator review. Passwords, tokens, credentials and other users are excluded.'}

def requests(c,actor,token):
    sessions.validate(c,actor,token)
    return {'items':[dict(r) for r in c.execute('SELECT id,kind,status,created_at,updated_at,ordinary_data_due_at,backup_target_at FROM account_privacy_requests WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 50',(actor,)).fetchall()]}

def create(c,actor,token,body):
    session=sessions.validate(c,actor,token)
    if time.time()-datetime.fromisoformat(session['created_at']).timestamp()>900:raise HTTPException(401,'Sign in again before submitting a privacy request.')
    security.lock(c,actor)
    previous=c.execute('SELECT id,kind,status FROM account_privacy_requests WHERE user_id=? AND request_id=?',(actor,str(body.request_id))).fetchone()
    if previous:
        if previous['kind']!=body.kind:raise HTTPException(409,'Use a new request after changing its type.')
        return {'id':previous['id'],'status':previous['status'],'data_deleted':False}
    pending=c.execute("SELECT id,status FROM account_privacy_requests WHERE user_id=? AND kind=? AND status NOT IN ('COMPLETED','REJECTED') ORDER BY created_at LIMIT 1",(actor,body.kind)).fetchone()
    if pending:return {'id':pending['id'],'status':pending['status'],'data_deleted':False}
    key=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO account_privacy_requests(id,user_id,request_id,kind,status,verified_session_id,policy_version,created_at,updated_at) VALUES(?,?,?,?,'REQUESTED',?,?,?,?)",(key,actor,str(body.request_id),body.kind,session['id'],POLICY,stamp,stamp))
    security.audit(c,actor,'PRIVACY_'+body.kind+'_REQUESTED')
    return {'id':key,'status':'REQUESTED','data_deleted':False,'message':'Request recorded for identity, workspace-authority and retention review. Requesting closure does not immediately delete data or grant a refund. Keep this reference for support.'}

def verify_closure(c,key,operator,review_reference):
    """Server-operator action after a scoped review; no data is purged.

    Not exposed through the customer API. Retention fulfillment requires its own
    scoped manifest, fresh backup and exceptions review before any deletion.
    """
    from app.config.settings import get_settings
    if operator not in get_settings().allowed_emails:raise HTTPException(403,'An authorized internal operator is required.')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{8,120}',review_reference):raise HTTPException(422,'A reviewed case reference is required.')
    row=c.execute("SELECT * FROM account_privacy_requests WHERE id=? AND kind='CLOSE_AND_DELETE'",(key,)).fetchone()
    if not row:raise HTTPException(404,'Closure request not found.')
    security.lock(c,row['user_id'])
    row=c.execute('SELECT * FROM account_privacy_requests WHERE id=?',(key,)).fetchone()
    if row['status']=='VERIFIED_CLOSURE':return {'id':key,'status':row['status'],'ordinary_data_due_at':row['ordinary_data_due_at'],'backup_target_at':row['backup_target_at'],'data_deleted':False}
    if row['status'] not in ('REQUESTED','REVIEW','AWAITING_INFORMATION'):raise HTTPException(409,'This request is not awaiting closure review.')
    stamp=int(time.time());created=now()
    if c.execute("UPDATE customer_accounts SET status='CLOSED',updated_at=? WHERE user_id=? AND status='ACTIVE'",(created,row['user_id'])).rowcount!=1:raise HTTPException(409,'Account state requires review before recording closure.')
    c.execute("UPDATE account_privacy_requests SET status='VERIFIED_CLOSURE',closure_verified_at=?,ordinary_data_due_at=?,backup_target_at=?,resolution_reference=?,updated_at=? WHERE id=?",(stamp,stamp+30*86400,stamp+90*86400,review_reference,created,key))
    for table in ('customer_sessions','account_login_tickets','account_recovery_tokens'):
        column='revoked_at' if table=='customer_sessions' else 'consumed_at'
        c.execute(f'UPDATE {table} SET {column}=? WHERE user_id=? AND {column} IS NULL',(created,row['user_id']))
    security.audit(c,row['user_id'],'ACCOUNT_CLOSURE_VERIFIED_BY_OPERATOR')
    return {'id':key,'status':'VERIFIED_CLOSURE','ordinary_data_due_at':stamp+30*86400,'backup_target_at':stamp+90*86400,'data_deleted':False}
