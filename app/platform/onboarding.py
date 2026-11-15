"""Resumable manual setup; completion checks persisted evidence, never seed flags."""
import json
import uuid
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from fastapi import HTTPException
from app.api.organization import require_role,membership_role,slugify
from app.database.prospects import now
from app.platform.context import current,organization

Objective=Literal['FIND_CUSTOMERS','FIND_DECISION_MAKERS','BUILD_LISTS','ENTER_MARKETS','ENRICH_LEADS','MANAGE_OUTREACH','MONITOR_SALES','RESEARCH_MARKETS','UNDERSTAND_CUSTOMER_NEEDS','MONITOR_BUYING_CONTEXT','MONITOR_COMPETITORS','EXPLORE_OPPORTUNITIES']

class Service(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=120)
    category:str=Field('',max_length=100)
    description:str=Field('',max_length=1000)

class Preferences(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    geography_mode:Literal['GLOBAL','SELECTED']='GLOBAL'
    countries:list[str]=Field(default_factory=list,max_length=50)
    geography_confirmed:bool=False
    integrations_skipped:bool=False
    start_discovery:Literal[False]=False
    setup_mode:Literal['MANUAL','AI']='MANUAL'
    company_review_id:UUID|None=None
    icp_review_id:UUID|None=None
    accepted_icp_ids:list[UUID]=Field(default_factory=list,max_length=3)
    research_keywords:list[str]=Field(default_factory=list,max_length=12)
    excluded_keywords:list[str]=Field(default_factory=list,max_length=12)

    @field_validator('research_keywords','excluded_keywords')
    @classmethod
    def research_terms(cls,values):
        if any(not v.strip() or len(v)>100 for v in values):raise ValueError('Use research terms of1–100 characters.')
        return list(dict.fromkeys(v.strip() for v in values))

    @field_validator('countries')
    @classmethod
    def countries_valid(cls,values):
        if any(not value or len(value)>100 for value in values):raise ValueError('Use country names of at most 100 characters.')
        return list(dict.fromkeys(values))

class Setup(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=0)
    current_step:Literal['OBJECTIVES','COMPANY','SERVICES','ICP','PREFERENCES','REVIEW']='OBJECTIVES'
    objectives:list[Objective]=Field(default_factory=list,max_length=7)
    services:list[Service]=Field(default_factory=list,max_length=20)
    default_icp_id:UUID|None=None
    preferences:Preferences=Field(default_factory=Preferences)

    @model_validator(mode='after')
    def unique_services(self):
        slugs=[slugify(service.name) for service in self.services]
        if len(slugs)!=len(set(slugs)):raise ValueError('Each service needs a distinct name.')
        return self

class Completion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=1)

def _lock(c,org):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    require_role(c,current().actor,org,('OWNER','ADMIN'))

def read(c):
    org=organization()
    require_role(c,current().actor,org,('OWNER','ADMIN','MEMBER','VIEWER'))
    row=c.execute('SELECT * FROM organization_setup WHERE organization_id=?',(org,)).fetchone()
    state=c.execute('SELECT status FROM organization_onboarding WHERE organization_id=?',(org,)).fetchone()
    services=[{'name':r['name'],'category':r['category'] or '', 'description':r['description'] or ''} for r in c.execute('SELECT name,category,description FROM organization_services WHERE organization_id=? AND active=1 ORDER BY name',(org,)).fetchall()]
    return {'revision':row['revision'] if row else 0,'current_step':row['current_step'] if row else 'OBJECTIVES',
        'objectives':json.loads(row['objectives_json']) if row else [],'services':services,
        'default_icp_id':row['default_icp_id'] if row else None,
        'preferences':Preferences.model_validate_json(row['preferences_json']).model_dump(mode='json') if row else Preferences().model_dump(),
        'status':state[0] if state else 'NOT_STARTED','can_edit':membership_role(c,current().actor,org) in ('OWNER','ADMIN')}

def _audit(c,action,revision):
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),current().actor,action,'organization:'+organization(),'SUCCESS',json.dumps({'revision':revision}),organization(),now()))

def save(c,body:Setup):
    org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'));_lock(c,org)
    previous=read(c)
    if previous['revision']!=body.revision:raise HTTPException(409,'Setup changed. Reload your saved progress before saving.')
    if body.default_icp_id:
        from app.icp.service import get
        get(c,str(body.default_icp_id))
    # References never authorize access; validate their persisted workspace owner.
    from app.platform.company_discovery import owned as owned_review
    for field,kind in (('company_review_id',('WEBSITE','DESCRIPTION')),('icp_review_id',('ICP_RECOMMENDATIONS',))):
        key=getattr(body.preferences,field)
        if key and owned_review(c,str(key))['source_kind'] not in kind:raise HTTPException(422,'Choose the matching setup review.')
    from app.icp.service import get as get_icp
    for key in body.preferences.accepted_icp_ids:get_icp(c,str(key))
    stamp=now();revision=body.revision+1
    c.execute('''INSERT INTO organization_setup(organization_id,default_icp_id,objectives_json,preferences_json,current_step,revision,updated_by,updated_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET default_icp_id=excluded.default_icp_id,
        objectives_json=excluded.objectives_json,preferences_json=excluded.preferences_json,current_step=excluded.current_step,
        revision=excluded.revision,updated_by=excluded.updated_by,updated_at=excluded.updated_at''',
        (org,str(body.default_icp_id) if body.default_icp_id else None,json.dumps(list(dict.fromkeys(body.objectives))),body.preferences.model_dump_json(),body.current_step,revision,current().actor,stamp))
    # Retain historical services instead of deleting records referenced by history.
    c.execute('UPDATE organization_services SET active=0,updated_at=? WHERE organization_id=?',(stamp,org))
    for service in body.services:
        c.execute('''INSERT INTO organization_services(id,organization_id,name,slug,category,description,active,source,created_at,updated_at)
            VALUES(?,?,?,?,?,?,1,'USER_CONFIRMED',?,?) ON CONFLICT(organization_id,slug) DO UPDATE SET name=excluded.name,
            category=excluded.category,description=excluded.description,active=1,source='USER_CONFIRMED',updated_at=excluded.updated_at''',
            (str(uuid.uuid4()),org,service.name,slugify(service.name),service.category,service.description,stamp,stamp))
    c.execute("UPDATE organization_onboarding SET current_step=?,updated_at=? WHERE organization_id=? AND status<>'COMPLETED'",(body.current_step,stamp,org))
    _audit(c,'ONBOARDING_PROGRESS_SAVED',revision)
    return read(c)

def completion_requirements(c,saved):
    from app.platform.company_profiles import read_profile
    company=read_profile(c);active_icp=False
    if saved['default_icp_id']:
        from app.icp.service import get
        try:active_icp=get(c,saved['default_icp_id'])['status']=='ACTIVE'
        except HTTPException as error:
            if error.status_code!=404:raise
    prefs=saved['preferences']
    return [
        {'id':'OBJECTIVES','title':'Business objectives','complete':bool(saved['objectives']),'message':'Choose a business objective'},
        {'id':'COMPANY','title':'Company profile','complete':bool(company['version']),'message':'Save your company profile'},
        {'id':'SERVICES','title':'Products and services','complete':bool(saved['services']),'message':'Confirm at least one product or service'},
        {'id':'ICP','title':'Ideal customers','complete':active_icp,'message':'Choose an active ideal customer profile'},
        {'id':'PREFERENCES','title':'Preferences','complete':bool(prefs['geography_confirmed'] and (prefs['geography_mode']!='SELECTED' or prefs['countries']) and prefs['integrations_skipped']),'message':'Confirm target geography and the optional integration setup choice'},
    ]


def progress(c):
    saved=read(c);steps=completion_requirements(c,saved)
    steps.append({'id':'REVIEW','title':'Review and finish','complete':saved['status']=='COMPLETED'})
    return {'status':saved['status'],'current_step':saved['current_step'],'completed_steps':sum(int(step['complete']) for step in steps),'total_steps':len(steps),'steps':[{key:value for key,value in step.items() if key!='message'} for step in steps],'can_edit':saved['can_edit']}


def complete(c,body:Completion):
    org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'));_lock(c,org)
    saved=read(c)
    if saved['revision']!=body.revision:raise HTTPException(409,'Setup changed. Reload your saved progress before completing.')
    completed=c.execute('SELECT completed_revision FROM organization_setup WHERE organization_id=?',(org,)).fetchone()
    if completed and completed[0]==body.revision:
        return {'status':'COMPLETED','discovery_started':False,'outreach_started':False}
    missing=[step['message'] for step in completion_requirements(c,saved) if not step['complete']]
    if missing:raise HTTPException(422,{'code':'SETUP_INCOMPLETE','message':'. '.join(missing)+'.'})
    stamp=now()
    c.execute("UPDATE organization_onboarding SET status='COMPLETED',current_step='COMPLETE',profile_completed=1,services_completed=1,audience_completed=1,preferences_completed=1,completed_at=COALESCE(completed_at,?),updated_at=? WHERE organization_id=?",(stamp,stamp,org))
    c.execute('UPDATE organization_setup SET completed_revision=? WHERE organization_id=?',(body.revision,org))
    _audit(c,'ONBOARDING_COMPLETED',body.revision)
    return {'status':'COMPLETED','discovery_started':False,'outreach_started':False}
