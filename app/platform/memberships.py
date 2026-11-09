"""Workspace membership administration shared by existing and future team APIs."""
import json
import uuid
from fastapi import HTTPException
from app.api.organization import ensure_user,membership_role
from app.api.permissions import require_owner
from app.database.prospects import now
from app.platform.context import organization


def change_role(c,actor,email,role):
    org=organization()
    require_owner(c,actor,org)
    role={'OPERATOR':'MEMBER'}.get(role,role)
    if role not in ('OWNER','ADMIN','MEMBER','VIEWER'):
        raise HTTPException(422,'Choose a supported workspace role.')
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:
        c.execute('BEGIN IMMEDIATE')
    # Recheck after the lock: concurrent requests cannot remove the final owner.
    require_owner(c,actor,org)
    before=membership_role(c,email,org)
    if before=='OWNER' and role!='OWNER':
        owners=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(org,)).fetchone()[0]
        if owners<=1:raise HTTPException(409,'The workspace must retain at least one active owner.')
    ensure_user(c,email)
    stamp=now()
    c.execute("""INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at)
        VALUES(?,?,?,?,'ACTIVE',?,?) ON CONFLICT(organization_id,user_id)
        DO UPDATE SET role=excluded.role,status='ACTIVE',updated_at=excluded.updated_at""",
        (str(uuid.uuid4()),org,email,role,stamp,stamp))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'MEMBERSHIP_ROLE_CHANGED','membership:'+email,'SUCCESS',json.dumps({'previous_role':before,'role':role}),org,stamp))
    return {'saved':True}
