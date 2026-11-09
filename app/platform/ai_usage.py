"""Committed reservations bound AI work even when provider requests fail."""
from datetime import datetime,timezone
from fastapi import HTTPException
from app.database.connection import db_session
from app.platform.context import organization,current
from app.api.organization import require_role
from app.database.prospects import now
from app.config.settings import get_settings

def reserve_icp():
    settings=get_settings()
    return reserve('ICP',settings.heysow_icp_ai_daily_limit,settings.heysow_icp_ai_global_daily_limit,'AI criteria')

def reserve_company():
    settings=get_settings()
    return reserve('COMPANY_PROFILE',settings.heysow_company_ai_daily_limit,settings.heysow_company_ai_global_daily_limit,'Company profile AI')

def reserve(feature,limit,global_limit,label):
    org=organization();actor=current().actor;day=datetime.now(timezone.utc).date().isoformat()
    with db_session() as c:
        require_role(c,actor,org,('OWNER','ADMIN'))
        if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945726)')
        elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
        total=c.execute('SELECT COALESCE(SUM(requests),0) FROM organization_ai_usage WHERE day=? AND feature=?',(day,feature)).fetchone()[0]
        row=c.execute('SELECT requests FROM organization_ai_usage WHERE organization_id=? AND day=? AND feature=?',(org,day,feature)).fetchone()
        if total>=global_limit:raise HTTPException(429,label+' capacity is exhausted for today. Manual editing remains available.')
        if row and row[0]>=limit:raise HTTPException(429,'This workspace has reached its daily '+label+' limit. Manual editing remains available.')
        c.execute('INSERT INTO organization_ai_usage(organization_id,day,feature,requests,updated_at) VALUES(?,?,?,1,?) ON CONFLICT(organization_id,day,feature) DO UPDATE SET requests=organization_ai_usage.requests+1,updated_at=excluded.updated_at',(org,day,feature,now()))

def icp_status(c):
    day=datetime.now(timezone.utc).date().isoformat();org=organization();settings=get_settings()
    row=c.execute("SELECT requests FROM organization_ai_usage WHERE organization_id=? AND day=? AND feature='ICP'",(org,day)).fetchone()
    return {'requests_used_today':row[0] if row else 0,'daily_limit':settings.heysow_icp_ai_daily_limit,'period_timezone':'UTC'}
