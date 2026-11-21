"""Personal workspace selection; does not grant membership or alter permissions."""
import uuid
from fastapi import HTTPException
from app.api.organization import membership_role,ensure_user
from app.database.prospects import now
from pydantic import BaseModel,ConfigDict,Field,field_validator
from uuid import UUID


def require_management_enabled():
    from app.config.settings import get_settings
    if not get_settings().heysow_workspace_management_enabled:
        raise HTTPException(503,'Workspace management is not enabled.')


class WorkspaceCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=2,max_length=120)
    request_id:UUID
    billing_account_id:UUID|None=None

    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if len(value)<2 or any(ord(ch)<32 for ch in value):raise ValueError('Enter a company name of at least two characters without control characters.')
        return value


class WorkspaceCreated(BaseModel):
    organization_id:UUID
    reused:bool


def create_workspace(c,actor,body:WorkspaceCreate):
    """An authenticated account explicitly creates and selects its own workspace."""
    from app.api.organization import create_organization
    ensure_user(c,actor)
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(actor,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    prior=c.execute('SELECT organization_id,requested_name FROM workspace_creation_requests WHERE user_id=? AND request_id=?',(actor,str(body.request_id))).fetchone()
    if prior:
        from app.billing import accounts
        if body.billing_account_id and accounts.anchor(c,prior['organization_id'])!=str(body.billing_account_id):raise HTTPException(409,'This request was already used with another billing account.')
        if prior['requested_name']!=body.name:raise HTTPException(409,'This creation request was already used for a different company name.')
        if not membership_role(c,actor,prior['organization_id']):raise HTTPException(404,'Created workspace is no longer available to this account.')
        # Retrying an old request must not switch the user's current workspace.
        return {'organization_id':prior['organization_id'],'reused':True}
    owned=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE user_id=? AND role='OWNER' AND status='ACTIVE'",(actor,)).fetchone()[0]
    from app.config.settings import get_settings
    if owned>=get_settings().heysow_workspace_creation_limit:raise HTTPException(409,'The current workspace creation safety limit has been reached for this account.')
    from app.billing import accounts
    account=str(body.billing_account_id) if body.billing_account_id else None
    if account and (not accounts.enabled() or not accounts.admin(c,account,actor)):raise HTTPException(403,'Choose an account you administer.')
    # An omitted account always creates an independent singleton, including for
    # an owner with exactly one administered account. Never infer consent.
    created=create_organization(c,actor,body.name,billing_account=account)
    org=created['organization_id']
    c.execute('INSERT INTO workspace_creation_requests(user_id,request_id,organization_id,requested_name,created_at) VALUES(?,?,?,?,?)',(actor,str(body.request_id),org,body.name,now()))
    select_workspace(c,actor,org)
    return {'organization_id':org,'reused':False}


def select_workspace(c,actor,organization_id):
    if not membership_role(c,actor,organization_id):
        raise HTTPException(404,'Workspace is unavailable for this account.')
    ensure_user(c,actor)
    stamp=now()
    c.execute('''INSERT INTO user_profiles(user_id,active_organization_id,created_at,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        active_organization_id=excluded.active_organization_id,updated_at=excluded.updated_at''',
        (actor,organization_id,stamp,stamp))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'WORKSPACE_SELECTED','organization:'+organization_id,'SUCCESS',organization_id,stamp))
    return {'organization_id':organization_id}


class WorkspaceRename(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=2,max_length=120)

    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if len(value)<2 or any(ord(ch)<32 for ch in value):raise ValueError('Enter a workspace name of at least two characters without control characters.')
        return value


def rename_workspace(c,actor,organization_id:str,body:WorkspaceRename):
    if membership_role(c,actor,organization_id)!='OWNER':
        raise HTTPException(403,'Only a workspace owner can rename a workspace.')
    row=c.execute("SELECT id,name FROM organizations WHERE id=? AND status='ACTIVE'",(organization_id,)).fetchone()
    if not row:raise HTTPException(404,'Workspace not found.')
    stamp=now()
    c.execute('UPDATE organizations SET name=?,updated_at=? WHERE id=?',(body.name,stamp,organization_id))
    c.execute('UPDATE organization_profiles SET display_name=?,updated_at=? WHERE organization_id=?',(body.name,stamp,organization_id))
    import json
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'ORGANIZATION_RENAMED','organization:'+organization_id,'SUCCESS',
         json.dumps({'previous_name':row['name'],'name':body.name}),organization_id,stamp))
    return {'organization_id':organization_id,'name':body.name}


def leave_workspace(c,actor,organization_id:str):
    role=membership_role(c,actor,organization_id)
    if not role:raise HTTPException(404,'Workspace membership not found.')
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(organization_id,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    if role=='OWNER':
        owners=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(organization_id,)).fetchone()[0]
        if owners<=1:
            raise HTTPException(409,'You are the last owner of this workspace. Assign another owner before leaving.')
    stamp=now()
    c.execute("UPDATE organization_memberships SET status='REVOKED',updated_at=? WHERE organization_id=? AND user_id=? AND status='ACTIVE'",(stamp,organization_id,actor))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'MEMBERSHIP_LEFT','organization:'+organization_id,'SUCCESS',organization_id,stamp))
    # If the user left their active workspace, switch active_organization_id to another remaining workspace (or NULL)
    prof=c.execute('SELECT active_organization_id FROM user_profiles WHERE user_id=?',(actor,)).fetchone()
    next_org=None
    if prof and prof['active_organization_id']==organization_id:
        fallback=c.execute(
            "SELECT m.organization_id FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id WHERE m.user_id=? AND m.status='ACTIVE' AND o.status='ACTIVE' ORDER BY m.created_at ASC LIMIT 1",
            (actor,),
        ).fetchone()
        next_org=fallback['organization_id'] if fallback else None
        c.execute('UPDATE user_profiles SET active_organization_id=?,updated_at=? WHERE user_id=?',(next_org,stamp,actor))
    return {'organization_id':organization_id,'left':True,'next_organization_id':next_org}


def enrich_memberships(c,rows,actor=None):
    import json
    from app.intent_radar.permissions import availability
    from app.billing import contracts
    from app.billing.subscription_access import product_grant,enabled as sub_enabled,entitlement_label
    from app.config.settings import get_settings
    enriched=[]
    settings_obj=get_settings()
    env=settings_obj.creem_environment
    for r in rows:
        org=r['organization_id']
        avail=availability(c,org)
        paid=contracts.active(c,org)
        grant=paid or (product_grant(c,org) if sub_enabled() else None)
        manual_row=c.execute("SELECT enabled FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR'",(org,)).fetchone()
        manual_granted=bool(manual_row and manual_row[0])
        plan_label=None
        plan_status=None
        if grant:
            plan_label=grant.get('entitlement_label') or ('Seven-day trial' if grant.get('source_kind')=='TRIAL' else 'Fixed-term access' if grant.get('source_kind')=='PAYMENT' else 'Active subscription')
            p_status=grant.get('provider_status') or avail.get('contract_status')
            if grant.get('is_trial'):
                plan_status='Canceled · Access remaining' if p_status in ('canceled','scheduled_cancel') else 'Trial active'
            elif p_status in ('canceled','scheduled_cancel'):
                plan_status='Canceled · Access remaining'
            else:
                plan_status='Active'
        elif manual_granted and avail.get('enabled'):
            plan_label='Approved Beta'
            plan_status='Active'
        else:
            c_row=c.execute(
                'SELECT p.plan_code,p.status,p.trial_start,p.period_start FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.organization_id=p.organization_id AND w.contract_id=p.id AND w.environment=p.environment WHERE p.organization_id=? AND p.environment=?',
                (org,env),
            ).fetchone() if sub_enabled() else None
            if c_row:
                plan_label=entitlement_label(c_row) or 'Previous plan'
                raw_st=(c_row['status'] or '').lower()
                plan_status='Expired' if raw_st in ('expired','canceled','past_due','unpaid','refunded','disputed') else raw_st.replace('_',' ').title() or 'Inactive'
            elif avail.get('enabled'):
                plan_label='Active Access'
                plan_status='Active'
            else:
                plan_label='No active plan'
                plan_status='Not activated'

        # Compute setup progress from actual persisted workspace evidence (never defaulting to 0/5 for configured workspaces)
        onb_row=c.execute(
            'SELECT status,current_step,profile_completed,services_completed,audience_completed,preferences_completed FROM organization_onboarding WHERE organization_id=?',
            (org,),
        ).fetchone()
        setup_row=c.execute(
            'SELECT current_step,objectives_json,default_icp_id,preferences_json,completed_revision FROM organization_setup WHERE organization_id=?',
            (org,),
        ).fetchone()
        prof_row=c.execute(
            'SELECT website_url,short_description,industry FROM organization_profiles WHERE organization_id=?',
            (org,),
        ).fetchone()
        svc_count=c.execute('SELECT COUNT(*) FROM organization_services WHERE organization_id=? AND active=1',(org,)).fetchone()[0]
        icp_count=c.execute("SELECT COUNT(*) FROM ideal_customer_profiles WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0]
        pref_row=c.execute('SELECT 1 FROM intent_preferences WHERE organization_id=?',(org,)).fetchone()

        onb_status=(onb_row['status'] if onb_row and onb_row['status'] else None) or avail.get('onboarding_status') or 'NOT_STARTED'
        try:
            objectives=json.loads(setup_row['objectives_json']) if setup_row and setup_row['objectives_json'] else []
        except Exception:
            objectives=[]
        try:
            setup_prefs=json.loads(setup_row['preferences_json']) if setup_row and setup_row['preferences_json'] else {}
        except Exception:
            setup_prefs={}

        has_business=bool(objectives or (prof_row and (prof_row['website_url'] or prof_row['short_description'] or prof_row['industry'])) or (onb_row and onb_row['profile_completed']))
        has_profile=bool((prof_row and (prof_row['short_description'] or prof_row['industry'])) or svc_count>0 or (onb_row and (onb_row['profile_completed'] and onb_row['services_completed'])))
        has_icp=bool((setup_row and setup_row['default_icp_id'] and icp_count>0) or icp_count>0 or (onb_row and onb_row['audience_completed']))
        has_research=bool((onb_row and onb_row['preferences_completed']) or setup_prefs.get('geography_confirmed') or setup_prefs.get('research_keywords') or pref_row)
        complete=onb_status=='COMPLETED'
        completed_steps=3 if complete else sum((has_business and has_profile,has_icp,has_research))
        next_setup_step=None if complete else ('welcome' if not has_business else 'company' if not has_profile else 'icp' if not has_icp else 'research')

        member_count=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0]
        from app.billing import accounts
        enriched.append({
            **r,
            'billing_account':accounts.summary(c,org,actor) if actor and accounts.enabled(org) else None,
            'plan_label':plan_label,
            'plan_status':plan_status,
            'access_state':avail.get('access_state'),
            'onboarding_status':onb_status,
            'onboarding_completed_steps':completed_steps,
            'onboarding_total_steps':3,
            'next_setup_step':next_setup_step,
            'member_count':member_count,
        })
    return enriched
