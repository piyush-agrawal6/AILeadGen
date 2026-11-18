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
    if not before:
        from app.billing.usage import capacity
        capacity(c,'team_members',c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0])
    ensure_user(c,email)
    stamp=now()
    c.execute("""INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at)
        VALUES(?,?,?,?,'ACTIVE',?,?) ON CONFLICT(organization_id,user_id)
        DO UPDATE SET role=excluded.role,status='ACTIVE',updated_at=excluded.updated_at""",
        (str(uuid.uuid4()),org,email,role,stamp,stamp))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'MEMBERSHIP_ROLE_CHANGED','membership:'+email,'SUCCESS',json.dumps({'previous_role':before,'role':role}),org,stamp))
    return {'saved':True}


def list_members(c,actor):
    org=organization()
    caller_role=membership_role(c,actor,org)
    if not caller_role:
        raise HTTPException(403,'Active workspace membership is required.')
    rows=c.execute(
        '''SELECT m.id,m.user_id,m.role,m.status,m.created_at,u.display_name,u.avatar_url
           FROM organization_memberships m LEFT JOIN users u ON u.id=m.user_id
           WHERE m.organization_id=? AND m.status='ACTIVE'
           ORDER BY CASE m.role WHEN 'OWNER' THEN 0 WHEN 'ADMIN' THEN 1 WHEN 'MEMBER' THEN 2 ELSE 3 END, m.created_at ASC, m.user_id ASC LIMIT 200''',
        (org,),
    ).fetchall()
    owner_count=sum(1 for r in rows if r['role']=='OWNER')
    seat_limit=None
    try:
        from app.billing.overview import overview
        ov=overview(c)
        for item in ov.get('usage',[]):
            if item.get('dimension')=='plan_team_members':
                seat_limit=item.get('limit')
                break
    except Exception:
        pass
    items=[]
    for r in rows:
        is_self=(r['user_id'].lower()==actor.lower())
        is_last_owner=(r['role']=='OWNER' and owner_count<=1)
        can_change_role=(caller_role=='OWNER' and not is_last_owner)
        can_remove=(
            not is_self
            and not is_last_owner
            and (caller_role=='OWNER' or (caller_role=='ADMIN' and r['role'] in ('MEMBER','VIEWER')))
        )
        items.append({
            'id':r['id'],
            'email':r['user_id'],
            'display_name':r['display_name'] or r['user_id'].split('@')[0],
            'avatar_url':r['avatar_url'],
            'role':r['role'],
            'status':r['status'],
            'joined_at':r['created_at'],
            'is_self':is_self,
            'primary_owner':is_last_owner,
            'can_change_role':can_change_role,
            'can_remove':can_remove,
        })
    return {
        'items':items,
        'total':len(items),
        'seat_used':len(items),
        'seat_limit':seat_limit,
        'caller_role':caller_role,
        'can_invite':caller_role in ('OWNER','ADMIN'),
        'can_manage_roles':caller_role=='OWNER',
    }


def remove_member(c,actor,target_email:str):
    org=organization()
    target_email=target_email.strip().lower()
    caller_role=membership_role(c,actor,org)
    if caller_role not in ('OWNER','ADMIN'):
        raise HTTPException(403,'Only workspace owners or administrators can remove members.')
    if target_email==actor.strip().lower():
        raise HTTPException(409,'Use Leave Workspace to remove yourself from this workspace.')
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:
        c.execute('BEGIN IMMEDIATE')
    caller_role=membership_role(c,actor,org)
    if caller_role not in ('OWNER','ADMIN'):
        raise HTTPException(403,'Workspace permission changed.')
    target_role=membership_role(c,target_email,org)
    if not target_role:
        raise HTTPException(404,'Active workspace member not found.')
    if caller_role=='ADMIN' and target_role in ('OWNER','ADMIN'):
        raise HTTPException(403,'Only a workspace owner can remove another owner or administrator.')
    if target_role=='OWNER':
        owners=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(org,)).fetchone()[0]
        if owners<=1:
            raise HTTPException(409,'The workspace must retain at least one active owner.')
    stamp=now()
    c.execute("UPDATE organization_memberships SET status='REVOKED',updated_at=? WHERE organization_id=? AND LOWER(user_id)=? AND status='ACTIVE'",(stamp,org,target_email))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'MEMBERSHIP_REMOVED','membership:'+target_email,'SUCCESS',json.dumps({'removed_role':target_role}),org,stamp))
    return {'removed':True,'email':target_email}
