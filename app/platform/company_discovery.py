"""One-page company setup extraction, never prospect discovery or qualification."""
import asyncio
import json
import hashlib
import uuid
from datetime import datetime,timedelta,timezone
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from fastapi import HTTPException
from app.platform.context import organization,current,job_scope
from app.api.organization import require_role
from app.database.prospects import now
from app.database.connection import db_session
from app.config.settings import get_settings


class DiscoveryCreate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    website:str=Field('',max_length=600)
    source_kind:Literal['WEBSITE','DESCRIPTION']='WEBSITE'
    description:str=Field('',max_length=6000)
    use_ai:bool=False
    request_id:uuid.UUID

    @field_validator('website')
    @classmethod
    def public_url(cls,value):
        from app.utils.urls import is_safe_url,_tld_extractor
        if not value:return value
        if '://' not in value:value='https://'+value
        if not is_safe_url(value,check_dns=False):raise ValueError('Enter a public HTTP or HTTPS company website.')
        if urlsplit(value).query or urlsplit(value).fragment:raise ValueError('Use a public website URL without query parameters or fragments.')
        domain=_tld_extractor(urlsplit(value).hostname or '')
        if not domain.domain or not domain.suffix:raise ValueError('Use a public company domain, not an IP address.')
        return value

    @model_validator(mode='after')
    def source_input(self):
        if self.source_kind=='WEBSITE' and (not self.website or self.description):raise ValueError('Enter a company website, or choose a business description instead.')
        if self.source_kind=='DESCRIPTION' and (self.website or len(self.description)<20 or not self.use_ai):raise ValueError('Describe your business in at least 20 characters to create an AI-assisted draft.')
        return self


def require_enabled():
    from app.platform.workspaces import require_management_enabled
    require_management_enabled()
    if not get_settings().heysow_company_discovery_enabled:raise HTTPException(503,'Company website extraction is not enabled.')


def owned(c,key):
    row=c.execute('SELECT * FROM organization_profile_jobs WHERE id=? AND organization_id=?',(key,organization())).fetchone()
    if not row:raise HTTPException(404,'Company website review not found.')
    return dict(row)


def detail(c,key):
    row=owned(c,key)
    expired=row['status']=='RUNNING' and row['lease_expires_at'] and row['lease_expires_at']<now()
    return {name:row[name] for name in ('id','website','status','error_code','created_at','updated_at','source_kind','progress_stage')}|{'preview':json.loads(row['result_json']) if row['result_json'] else None,'can_retry':row['attempts']<3 and (row['status']=='FAILED' or bool(expired))}


def control(c,key,action):
    require_enabled();require_role(c,current().actor,organization(),('OWNER','ADMIN'))
    row=owned(c,key)
    if action=='CANCEL':
        c.execute("UPDATE organization_profile_jobs SET status='CANCELLED',lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND organization_id=? AND status IN ('QUEUED','RUNNING')",(now(),key,organization()))
    elif action=='RETRY':
        if not detail(c,key)['can_retry']:raise HTTPException(409,'This review cannot be retried now. Create a new review if necessary.')
        require_role(c,row['created_by'],organization(),('OWNER','ADMIN'))
        c.execute("UPDATE organization_profile_jobs SET status='QUEUED',error_code=NULL,execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND organization_id=? AND attempts<3 AND (status='FAILED' OR (status='RUNNING' AND lease_expires_at<?))",(now(),key,organization(),now()))
    else:raise HTTPException(422,'Choose a supported review action.')
    return detail(c,key)


class PreviewApply(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    profile_version:str|None=Field(None,max_length=100)
    fields:dict[Literal['name','website','description','city','country','industry','contact_email'],str]=Field(min_length=1,max_length=7)


def confirm(c,key,body:PreviewApply):
    require_enabled();org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'))
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    require_role(c,current().actor,org,('OWNER','ADMIN'))
    row=owned(c,key)
    if row['status']!='READY' or not row['result_json']:raise HTTPException(409,'The website review is not ready to confirm.')
    if datetime.now(timezone.utc)-datetime.fromisoformat(row['updated_at'])>timedelta(days=7):raise HTTPException(409,'This website preview has expired. Create a new review.')
    from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate
    previous=read_profile(c)
    digest=hashlib.sha256(json.dumps(body.model_dump(),sort_keys=True).encode()).hexdigest()
    if row['confirmed_hash']==digest:return previous
    if previous['version']!=body.profile_version:raise HTTPException(409,'Company profile changed. Reload it before confirming this preview.')
    preview=json.loads(row['result_json'])
    values={name:value for name,value in previous.items() if name in CompanyUpdate.model_fields}
    values.update(body.fields);values['version']=body.profile_version
    result=save_profile(c,CompanyUpdate.model_validate(values))
    stamp=now()
    for field,value in body.fields.items():
        candidate=preview['suggestions'].get(field)
        if candidate is None:continue
        confirmed=candidate==value
        c.execute("INSERT INTO organization_profile_sources(id,organization_id,source_type,source_url,field_name,extracted_value_json,detected_at,confirmed_by_user,confirmed_at) VALUES(?,?,'WEBSITE_EXTRACTED',?,?,?,?,?,?)",(str(uuid.uuid4()),org,preview['source_url'],field,json.dumps(candidate),preview['retrieved_at'],int(confirmed),stamp if confirmed else None))
        if confirmed:c.execute("INSERT INTO organization_profile_sources(id,organization_id,source_type,source_url,field_name,extracted_value_json,detected_at,confirmed_by_user,confirmed_at) VALUES(?,?,'USER_CONFIRMED',?,?,?,?,1,?)",(str(uuid.uuid4()),org,preview['source_url'],field,json.dumps(value),stamp,stamp))
    c.execute('UPDATE organization_profile_jobs SET confirmed_hash=? WHERE id=? AND organization_id=?',(digest,key,org))
    return result


def create(c,body):
    require_enabled();org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'))
    if body.use_ai:
        from app.platform.company_autofill import require_ai,capabilities
        require_ai()
        if not capabilities(c)['configured']:raise HTTPException(503,'The AI gateway is unavailable. You can still enter company details manually.')
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    require_role(c,current().actor,org,('OWNER','ADMIN'))
    digest=hashlib.sha256(json.dumps(body.model_dump(exclude={'request_id'}),sort_keys=True).encode()).hexdigest()
    prior=c.execute('SELECT * FROM organization_profile_jobs WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
    if prior:
        prior_hash=prior['input_hash'] or hashlib.sha256(json.dumps({'website':prior['website'],'source_kind':'WEBSITE','description':'','use_ai':False},sort_keys=True).encode()).hexdigest()
        if prior_hash!=digest:raise HTTPException(409,'This review request already belongs to different company information.')
        return detail(c,prior['id'])
    fresh=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
    cached=c.execute("SELECT id,created_by FROM organization_profile_jobs WHERE organization_id=? AND (input_hash=? OR (input_hash='' AND website=? AND use_ai=0 AND ?=0)) AND ((status='READY' AND updated_at>?) OR status='QUEUED' OR (status='RUNNING' AND lease_expires_at>?)) ORDER BY updated_at DESC LIMIT 1",(org,digest,body.website,int(body.use_ai),fresh,now())).fetchone()
    if cached:
        # Never reuse a queued job whose creator has lost authorization.
        require_role(c,cached['created_by'],org,('OWNER','ADMIN'))
        return detail(c,cached['id'])
    cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    count=c.execute('SELECT COUNT(*) FROM organization_profile_jobs WHERE organization_id=? AND created_at>?',(org,cutoff)).fetchone()[0]
    if count>=get_settings().heysow_company_discovery_hourly_limit:raise HTTPException(429,'This workspace has reached its hourly company website review limit.')
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945724)')
    total=c.execute('SELECT COUNT(*) FROM organization_profile_jobs WHERE created_at>?',(cutoff,)).fetchone()[0]
    if total>=get_settings().heysow_company_discovery_global_hourly_limit:raise HTTPException(429,'Company website review capacity is temporarily exhausted. Retry later.')
    key=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO organization_profile_jobs(id,organization_id,created_by,request_id,website,status,created_at,updated_at,source_kind,input_text,use_ai,input_hash,progress_stage) VALUES(?,?,?,?,?,'QUEUED',?,?,?,?,?,?,'QUEUED')",(key,org,current().actor,str(body.request_id),body.website,stamp,stamp,body.source_kind,body.description,int(body.use_ai),digest))
    return detail(c,key)


def parse_preview(html,url):
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser');values={};sources={}
    def text(value,limit):return ' '.join(str(value).split())[:limit] if isinstance(value,(str,int)) else ''
    def add(field,value,limit,kind):
        value=text(value,limit)
        if value and field not in values:values[field]=value;sources[field]={'url':url,'kind':kind}
    organizations=[]
    def collect(value,depth=0):
        if depth>5:return
        if isinstance(value,list):
            for item in value[:30]:collect(item,depth+1)
        elif isinstance(value,dict):
            types=value.get('@type',[]);types=[types] if isinstance(types,str) else types
            if isinstance(types,list) and any(kind in ('Organization','LocalBusiness','Corporation','ProfessionalService','Hotel','MedicalBusiness') for kind in types):organizations.append(value)
            collect(value.get('@graph'),depth+1)
    for script in soup.find_all('script',type='application/ld+json')[:10]:
        raw=script.string or script.get_text()
        if len(raw)>100000:continue
        try:collect(json.loads(raw))
        except (ValueError,TypeError):continue
    for company in organizations[:5]:
        add('name',company.get('name'),120,'STRUCTURED_DATA');add('description',company.get('description'),1000,'STRUCTURED_DATA')
        address=company.get('address')
        if isinstance(address,dict):
            add('city',address.get('addressLocality'),100,'STRUCTURED_DATA');add('country',address.get('addressCountry'),100,'STRUCTURED_DATA')
        email=company.get('email')
        if isinstance(email,str):
            from app.mail.contacted import normalize
            add('contact_email',normalize(email.removeprefix('mailto:')),254,'STRUCTURED_DATA')
    site=soup.find('meta',property='og:site_name')
    if site:add('name',site.get('content'),120,'WEBSITE_METADATA')
    meta=soup.find('meta',attrs={'name':'description'})
    if meta:add('description',meta.get('content'),1000,'WEBSITE_METADATA')
    if soup.title:add('name',soup.title.get_text(' ',strip=True),120,'PAGE_TITLE_REVIEW_REQUIRED')
    add('website',url,600,'REVIEWED_URL')
    # No prose instruction from HTML is executed. Only bounded literal fields
    # enter the owner-review preview; no company profile is changed here.
    return {'suggestions':values,'sources':sources,'source_url':url,'retrieved_at':now(),'ownership_verified':False,'pages_reviewed':1}


async def fetch_preview(website):
    if get_settings().app_env=='test':raise RuntimeError('Live company website requests are disabled in offline tests.')
    from app.utils.http import SafeAsyncClient
    from app.utils.urls import _tld_extractor
    async with SafeAsyncClient(timeout=12,max_bytes=1000000,redirect_limit=3) as client:
        response=await client.get(website)
        response.raise_for_status()
        source=str(response.url)
        original=_tld_extractor(urlsplit(website).hostname or '')
        final=_tld_extractor(urlsplit(source).hostname or '')
        if original.top_domain_under_public_suffix!=final.top_domain_under_public_suffix:raise ValueError('Website redirected to another organization domain')
        if 'html' not in response.headers.get('content-type','').lower():raise ValueError('Website did not return HTML')
        return parse_preview(response.text,source)


def execute(key,db_path=None):
    require_enabled()
    from app.database.migrations import verify_schema
    lease=str(uuid.uuid4())
    with db_session(db_path) as scope:
        verify_schema(scope)
        with job_scope(scope,'company_profile',key):
            require_enabled()
            require_role(scope,current().actor,organization(),('OWNER','ADMIN'))
            with db_session(db_path) as c:
                row=owned(c,key)
                if row['status'] not in ('QUEUED','RUNNING'):return
                expiry=(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat()
                changed=c.execute("UPDATE organization_profile_jobs SET status='RUNNING',lease_owner=?,lease_expires_at=?,attempts=attempts+1,updated_at=? WHERE id=? AND organization_id=? AND attempts<3 AND (status='QUEUED' OR (status='RUNNING' AND lease_expires_at<?))",(lease,expiry,now(),key,organization(),now())).rowcount
                if changed!=1:return
            def active(stage=None):
                require_enabled()
                if row['use_ai']:
                    from app.platform.company_autofill import require_ai
                    require_ai()
                with db_session(db_path) as c:
                    require_role(c,row['created_by'],organization(),('OWNER','ADMIN'))
                    present=owned(c,key)
                    if present['status']!='RUNNING' or present['lease_owner']!=lease or present['lease_expires_at']<now():raise HTTPException(409,'Company review is no longer active.')
                    if stage:c.execute('UPDATE organization_profile_jobs SET progress_stage=? WHERE id=? AND organization_id=? AND lease_owner=?',(stage,key,organization(),lease))
            try:
                active('ANALYZING' if row['source_kind']=='DESCRIPTION' else 'READING_WEBSITE')
                if row['use_ai']:
                    from app.platform.company_autofill import generate
                    with db_session(db_path) as c:result=asyncio.run(asyncio.wait_for(generate(c,row,active),timeout=65))
                else:result=asyncio.run(asyncio.wait_for(fetch_preview(row['website']),timeout=25))
            except Exception:
                with db_session(db_path) as c:c.execute("UPDATE organization_profile_jobs SET status='FAILED',progress_stage='FAILED',error_code='WEBSITE_REVIEW_FAILED',lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND organization_id=? AND lease_owner=? AND status='RUNNING'",(now(),key,organization(),lease))
                return
            with db_session(db_path) as c:
                # A revoked/cancelled job cannot apply a late result.
                require_role(c,row['created_by'],organization(),('OWNER','ADMIN'))
                c.execute("UPDATE organization_profile_jobs SET status='READY',progress_stage='READY',result_json=?,error_code=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND organization_id=? AND lease_owner=? AND status='RUNNING'",(json.dumps(result),now(),key,organization(),lease))
