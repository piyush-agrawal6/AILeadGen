"""Owned company profile edits, with provenance and optimistic concurrency."""
import json
import hashlib
import uuid
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from uuid import UUID
from app.api.organization import require_role,membership_role
from app.database.prospects import now
from app.platform.context import current,organization

class CompanyService(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=120)
    category:str=Field('',max_length=100)
    description:str=Field('',max_length=1000)


class CompanyFields(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=120)
    website:str=Field('',max_length=600)
    description:str=Field('',max_length=1000)
    industry:str=Field('',max_length=100)
    company_size:str=Field('',max_length=60)
    country:str=Field('',max_length=100)
    city:str=Field('',max_length=100)
    timezone:str=Field('UTC',max_length=80)
    contact_email:str=Field('',max_length=254)
    countries_served:list[str]=Field(default_factory=list,max_length=50)
    target_customers:list[str]=Field(default_factory=list,max_length=50)
    target_industries:list[str]=Field(default_factory=list,max_length=50)
    specialties:list[str]=Field(default_factory=list,max_length=30)
    positioning:str=Field('',max_length=1000)
    products_services:list[CompanyService]=Field(default_factory=list,max_length=20)

    @field_validator('website')
    @classmethod
    def public_website(cls,value):
        from app.utils.urls import is_safe_url
        if value and not is_safe_url(value,check_dns=False):raise ValueError('Enter a public HTTP or HTTPS website.')
        return value

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls,value):
        try:ZoneInfo(value)
        except (ValueError,ZoneInfoNotFoundError):raise ValueError('Choose a valid timezone.')
        return value

    @field_validator('contact_email')
    @classmethod
    def business_email(cls,value):
        from app.mail.contacted import normalize
        if value and not normalize(value):raise ValueError('Enter a valid business contact email.')
        return normalize(value) or ''

    @field_validator('countries_served','target_customers','target_industries','specialties')
    @classmethod
    def countries(cls,values):
        if values is None:return None
        result=[]
        for value in values:
            value=value.strip()
            if not value or len(value)>100:raise ValueError('Use country names of at most 100 characters.')
            if value not in result:result.append(value)
        return result

    @field_validator('products_services')
    @classmethod
    def distinct_services(cls,values):
        if values is None:return None
        from app.api.organization import slugify
        slugs=[slugify(item.name) for item in values]
        if len(set(slugs))!=len(slugs):raise ValueError('Each product or service needs a distinct name.')
        return values

class CompanyUpdate(CompanyFields):
    version:str|None=Field(None,max_length=100)
    # Older callers omit these fields; omission must preserve newer saved data.
    target_customers:list[str]|None=Field(None,max_length=50)
    target_industries:list[str]|None=Field(None,max_length=50)
    specialties:list[str]|None=Field(None,max_length=30)
    positioning:str|None=Field(None,max_length=1000)
    products_services:list[CompanyService]|None=Field(None,max_length=20)
    review_id:UUID|None=None
    reviewed_fields:list[str]=Field(default_factory=list,max_length=20)

class CompanyProfile(CompanyFields):
    organization_id:str
    version:str|None
    can_edit:bool
    onboarding_status:str

COLUMNS={'website':'website_url','description':'short_description','industry':'industry',
         'company_size':'company_size','country':'country','city':'city','timezone':'timezone',
         'contact_email':'contact_email','countries_served':'service_regions_json',
         'target_customers':'target_customer_types_json','target_industries':'target_industries_json',
         'positioning':'long_description','specialties':'specialties_json'}
ARRAY_FIELDS=frozenset(('countries_served','target_customers','target_industries','specialties'))


def read_profile(c):
    org=organization();actor=current().actor
    row=c.execute('SELECT * FROM organization_profiles WHERE organization_id=?',(org,)).fetchone()
    company=c.execute('SELECT name FROM organizations WHERE id=?',(org,)).fetchone()
    if not company:raise HTTPException(404,'Workspace not found.')
    state=c.execute('SELECT status FROM organization_onboarding WHERE organization_id=?',(org,)).fetchone()
    data={'name':row['display_name'] or company['name'] if row else company['name']}
    for field,column in COLUMNS.items():
        value=row[column] if row else None
        data[field]=json.loads(value or '[]') if field in ARRAY_FIELDS else value or ('UTC' if field=='timezone' else '')
    data['products_services']=[{'name':item['name'],'category':item['category'] or '','description':item['description'] or ''} for item in c.execute('SELECT name,category,description FROM organization_services WHERE organization_id=? AND active=1 ORDER BY name',(org,)).fetchall()]
    version=hashlib.sha256(json.dumps({'fields':data,'updated_at':row['updated_at']},sort_keys=True).encode()).hexdigest() if row else None
    return {**data,'organization_id':org,'version':version,
            'can_edit':membership_role(c,actor,org) in ('OWNER','ADMIN'),
            'onboarding_status':state[0] if state else 'NOT_STARTED'}


def save_profile(c,body):
    org=organization();actor=current().actor
    require_role(c,actor,org,('OWNER','ADMIN'))
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    require_role(c,actor,org,('OWNER','ADMIN'))
    before=read_profile(c)
    if before['version']!=body.version:raise HTTPException(409,'Company profile changed. Reload it before saving.')
    values=body.model_dump(exclude={'version','review_id','reviewed_fields'})
    for key in ('target_customers','target_industries','specialties','positioning','products_services'):
        if values[key] is None:values[key]=before[key]
    # Validate preserved values too, without accepting arbitrary provenance claims.
    values=CompanyFields.model_validate(values).model_dump()
    preview=None
    if body.review_id:
        from datetime import datetime,timezone,timedelta
        row=c.execute("SELECT result_json,updated_at,status FROM organization_profile_jobs WHERE id=? AND organization_id=?",(str(body.review_id),org)).fetchone()
        if not row:raise HTTPException(404,'Company review not found.')
        if row['status']!='READY' or not row['result_json'] or datetime.now(timezone.utc)-datetime.fromisoformat(row['updated_at'])>timedelta(days=7):raise HTTPException(409,'Company review is unavailable or expired. Analyze again before applying suggestions.')
        preview=json.loads(row['result_json'])
        if any(field not in preview.get('suggestions',{}) or field not in CompanyFields.model_fields for field in body.reviewed_fields):raise HTTPException(422,'Choose fields actually returned by this company review.')
    changed=[key for key,value in values.items() if before[key]!=value]
    if not changed and before['version'] is not None and not body.review_id:return before
    if before['version'] is None and not changed:changed=['name']
    stamp=now()
    c.execute('UPDATE organizations SET name=?,updated_at=? WHERE id=?',(body.name,stamp,org))
    columns=['display_name',*COLUMNS.values()]
    stored=[body.name,*[json.dumps(values[key]) if key in ARRAY_FIELDS else values[key] for key in COLUMNS]]
    names=','.join(columns)
    c.execute('INSERT INTO organization_profiles(organization_id,'+names+',created_at,updated_at) VALUES('+','.join('?' for _ in range(len(stored)+3))+') ON CONFLICT(organization_id) DO UPDATE SET '+','.join(column+'=excluded.'+column for column in columns)+',updated_at=excluded.updated_at',[org,*stored,stamp,stamp])
    for key in changed:
        c.execute("INSERT INTO organization_profile_sources(id,organization_id,source_type,field_name,extracted_value_json,detected_at,confirmed_by_user,confirmed_at) VALUES(?,?,'USER_ENTERED',?,?,?,1,?)",(str(uuid.uuid4()),org,key,json.dumps(values[key]),stamp,stamp))
    if 'products_services' in changed:
        from app.api.organization import slugify
        c.execute('UPDATE organization_services SET active=0,updated_at=? WHERE organization_id=?',(stamp,org))
        for item in values['products_services']:
            c.execute("INSERT INTO organization_services(id,organization_id,name,slug,category,description,active,source,created_at,updated_at) VALUES(?,?,?,?,?,?,1,'USER_CONFIRMED',?,?) ON CONFLICT(organization_id,slug) DO UPDATE SET name=excluded.name,category=excluded.category,description=excluded.description,active=1,source='USER_CONFIRMED',updated_at=excluded.updated_at",(str(uuid.uuid4()),org,item['name'],slugify(item['name']),item['category'],item['description'],stamp,stamp))
    if preview:
        for field in body.reviewed_fields:
            candidate=preview['suggestions'][field];source=preview.get('sources',{}).get(field,{})
            source_type='AI_INFERRED' if preview.get('ai_assisted') else 'WEBSITE_EXTRACTED'
            confirmed=candidate==values[field]
            c.execute('INSERT INTO organization_profile_sources(id,organization_id,source_type,source_url,field_name,extracted_value_json,confidence,detected_at,confirmed_by_user,confirmed_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (str(uuid.uuid4()),org,source_type,source.get('url'),field,json.dumps(candidate),'REVIEWED_PROPOSAL' if confirmed else 'EDITED_BY_USER',preview['retrieved_at'],int(confirmed),stamp if confirmed else None))
    c.execute("UPDATE organization_onboarding SET profile_completed=1,status=CASE WHEN status='COMPLETED' THEN status ELSE 'IN_PROGRESS' END,current_step=CASE WHEN status='COMPLETED' THEN current_step ELSE 'SERVICES' END,updated_at=? WHERE organization_id=?",(stamp,org))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),actor,'COMPANY_PROFILE_UPDATED','organization:'+org,'SUCCESS',json.dumps({'fields':changed}),org,stamp))
    return read_profile(c)
