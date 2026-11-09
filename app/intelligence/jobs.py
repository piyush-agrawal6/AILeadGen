"""Enrichment/discovery/verification with durable leases and no mail side effects."""
import asyncio,hashlib,json,uuid,time
from datetime import datetime,timedelta,timezone
from typing import Literal,Annotated
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.database.connection import db_session
from app.database.prospects import now
from app.platform.context import current,job_scope
from app.people.service import ctx,company,get as person,save,Person
from app.config.settings import get_settings
class Start(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['COMPANY_ENRICH','CONTACT_DISCOVER','CONTACT_ENRICH','CONTACT_VERIFY','COMPANY_SUMMARIZE','ASSISTANT_TURN']
    resource_ids:list[Annotated[str,Field(min_length=1,max_length=60)]]=Field(min_length=1,max_length=100)
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    reuse_days:int=Field(7,ge=0,le=90)

def owned(c,key):
    context=ctx(c);row=c.execute('SELECT * FROM intelligence_jobs WHERE id=? AND organization_id=?',(key,context.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Intelligence job not found.')
    return dict(row)

def detail(c,key,page=1,size=25):
    result=owned(c,key);result.pop('fingerprint');result.pop('lease_owner');result['configuration']=json.loads(result.pop('configuration_json'))
    result['counts']={r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM intelligence_job_items WHERE job_id=? GROUP BY status',(key,)).fetchall()}
    result['total']=sum(result['counts'].values());result['page']=page;result['page_size']=size
    result['items']=[{**dict(r),'result':json.loads(r['result_json'])} for r in c.execute('SELECT * FROM intelligence_job_items WHERE job_id=? ORDER BY id LIMIT ? OFFSET ?',(key,size,(page-1)*size)).fetchall()]
    for item in result['items']:item.pop('result_json')
    result['usage']={'requested_records':result['total'],'provider':'STORED_EVIDENCE_THEN_PUBLIC_WEBSITE_OR_DNS','monetary_cost':None,'cost_state':'NOT_REPORTED','recipient_delivery_verified':False}
    return result

def listing(c,status='',page=1,size=25):
    org=ctx(c).organization_id;where='organization_id=?';args=[org]
    if status:where+=' AND status=?';args.append(status)
    total=c.execute('SELECT COUNT(*) FROM intelligence_jobs WHERE '+where,args).fetchone()[0]
    rows=c.execute('SELECT id,kind,status,created_at,updated_at,completed_at,error_code,attempts FROM intelligence_jobs WHERE '+where+' ORDER BY created_at DESC,id LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()
    return {'items':[dict(row) for row in rows],'total':total,'page':page,'page_size':size}

def create(c,body):
    context=ctx(c,True);ids=list(dict.fromkeys(body.resource_ids))
    if body.kind=='COMPANY_SUMMARIZE':
        from app.api.organization import require_role
        require_role(c,context.actor,context.organization_id,('OWNER','ADMIN'))
        if not get_settings().heysow_company_ai_enabled:raise HTTPException(503,'Company AI summaries are disabled.')
    for key in ids:
        if body.kind=='ASSISTANT_TURN':
            from app.assistant.service import turn
            from app.api.organization import require_role
            require_role(c,context.actor,context.organization_id,('OWNER','ADMIN'))
            if not get_settings().heysow_lead_assistant_enabled:raise HTTPException(503,'The Lead Engine assistant is disabled.')
            turn(c,key)
        elif body.kind in ('COMPANY_ENRICH','CONTACT_DISCOVER','COMPANY_SUMMARIZE'):
            if not key.isdigit() or not 1<=int(key)<=9223372036854775807:raise HTTPException(422,'Choose company record IDs.')
            company(c,int(key))
        else:
            if person(c,key)['archived_at']:raise HTTPException(409,'Archived contacts are preserved but cannot be enriched.')
    cfg={'kind':body.kind,'resource_ids':ids,'reuse_days':body.reuse_days};fingerprint=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    from app.workflows.service import lock
    lock(c);previous=c.execute('SELECT id,fingerprint FROM intelligence_jobs WHERE organization_id=? AND request_id=?',(context.organization_id,str(body.request_id))).fetchone()
    if previous:
        if previous['fingerprint']!=fingerprint:raise HTTPException(409,'Job request ID belongs to different content.')
        return detail(c,previous['id'])
    limits=get_settings();active=c.execute("SELECT COUNT(*) FROM intelligence_jobs WHERE organization_id=? AND status IN ('QUEUED','RUNNING')",(context.organization_id,)).fetchone()[0]
    if active>=limits.intelligence_active_jobs:raise HTTPException(429,'Finish or cancel an existing enrichment job first.')
    used=c.execute('SELECT COUNT(*) FROM intelligence_job_items i JOIN intelligence_jobs j ON j.id=i.job_id WHERE j.organization_id=? AND j.created_at>=?',(context.organization_id,datetime.now(timezone.utc).date().isoformat())).fetchone()[0]
    if used+len(ids)>limits.intelligence_daily_records:raise HTTPException(429,'Daily enrichment record limit reached.')
    key=str(uuid.uuid4());stamp=now();c.execute('INSERT INTO intelligence_jobs(id,organization_id,created_by,kind,request_id,fingerprint,configuration_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(key,context.organization_id,context.actor,body.kind,str(body.request_id),fingerprint,json.dumps(cfg),stamp,stamp))
    for resource in ids:c.execute('INSERT INTO intelligence_job_items(id,job_id,resource_id,updated_at) VALUES(?,?,?,?)',(str(uuid.uuid4()),key,resource,stamp))
    return detail(c,key)

def control(c,key,action):
    ctx(c,True);row=owned(c,key)
    if action=='cancel':c.execute("UPDATE intelligence_jobs SET status='CANCELLED',updated_at=? WHERE id=? AND organization_id=? AND status IN ('RUNNING','QUEUED')",(now(),key,row['organization_id']))
    elif action=='retry':
        if row['attempts']>=3 or row['dispatch_attempts']>=3:raise HTTPException(409,'Retry limit reached; review the recorded failures.')
        if row['status'] not in ('FAILED','PARTIAL') and not(row['status']=='RUNNING' and row['lease_until'] and row['lease_until']<now()):raise HTTPException(409,'This job cannot be retried yet.')
        if row['created_by']!=current().actor:raise HTTPException(409,'The original authorized job owner must retry this job.')
        c.execute("UPDATE intelligence_job_items SET status='QUEUED',error_code=NULL WHERE job_id=? AND status IN ('FAILED','PROCESSING','QUEUED')",(key,));c.execute("UPDATE intelligence_jobs SET status='QUEUED',lease_owner=NULL,lease_until=NULL,execution_name=NULL,error_code=NULL,updated_at=? WHERE id=? AND organization_id=?",(now(),key,row['organization_id']))
    return detail(c,key)

async def run_item(c,row,item,configuration):
    kind=row['kind'];resource=item['resource_id'];ctx(c,True)
    if kind=='ASSISTANT_TURN':
        from app.assistant.service import process
        return await process(c,resource)
    if kind=='CONTACT_VERIFY':
        from app.people.verification import check
        contact=person(c,resource)
        if contact['archived_at']:raise HTTPException(409,'Contact was archived.')
        if not contact['work_email']:return {'status':'UNAVAILABLE','reason':'NO_BUSINESS_EMAIL'}
        result=await asyncio.to_thread(check,contact['work_email']);ctx(c,True);latest=person(c,resource)
        if latest['revision']!=contact['revision'] or latest['work_email']!=contact['work_email']:raise HTTPException(409,'Contact changed during verification.')
        data=latest['evidence'];data['verification']=result
        changed=c.execute('UPDATE contact_people SET revision=revision+1,verification_state=?,evidence_json=?,checked_at=?,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(result['state'],json.dumps(data),now(),now(),resource,row['organization_id'],contact['revision'])).rowcount
        if not changed:raise HTTPException(409,'Contact changed during verification.')
        return {'status':'COMPLETE',**result}
    contact=person(c,resource) if kind=='CONTACT_ENRICH' else None
    if contact and contact['archived_at']:raise HTTPException(409,'Contact was archived.')
    b=company(c,contact['business_id'] if contact else int(resource));tags=json.loads(b['source_tags_json'] or '{}');facts=tags.get('company_intelligence',{});fresh=False
    try:fresh=facts.get('status')=='COMPLETE' and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(facts['retrieved_at'])).total_seconds()<configuration['reuse_days']*86400
    except (ValueError,KeyError,TypeError):pass
    if kind=='COMPANY_SUMMARIZE':
        from app.intelligence.summary import generate,digest
        previous=tags.get('company_summary',{})
        if previous.get('status')=='COMPLETE' and previous.get('input_hash')==digest(facts):return {'status':'COMPLETE','mode':'CACHED','summary':previous}
        result=await generate(c,facts);ctx(c,True);latest=company(c,b['id'])
        if result['status']=='COMPLETE':
            data=json.loads(latest['source_tags_json'] or '{}')
            if digest(data.get('company_intelligence',{}))!=digest(facts):raise HTTPException(409,'Company evidence changed while generating the summary.')
            data['company_summary']=result;c.execute('UPDATE businesses SET source_tags_json=?,updated_at=? WHERE id=? AND run_id IN (SELECT id FROM pipeline_runs WHERE organization_id=?)',(json.dumps(data),now(),b['id'],row['organization_id']))
        return result
    if not b['website']:return {'status':'UNAVAILABLE','reason':'NO_COMPANY_WEBSITE'}
    from app.enrichment.crawler import WebsiteCrawler
    from app.prospecting.intake import evidence
    crawler=WebsiteCrawler(max_pages=3,page_timeout=6,max_duration=22,max_response_bytes=500000)
    # CONTACT_ENRICH/DISCOVER need the source markup, not only cached excerpts.
    if fresh and kind=='COMPANY_ENRICH':return {'status':'COMPLETE','mode':'CACHED','pages':len(facts.get('pages',[]))}
    contacts_cache=tags.get('professional_contacts',{});cached_contacts=False
    try:cached_contacts=kind in ('CONTACT_DISCOVER','CONTACT_ENRICH') and contacts_cache.get('website')==b['website'] and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(contacts_cache['retrieved_at'])).total_seconds()<configuration['reuse_days']*86400
    except (ValueError,KeyError,TypeError):pass
    crawl=None if cached_contacts else await asyncio.wait_for(crawler.crawl(b['website']),timeout=25)
    ctx(c,True);latest=company(c,b['id'])
    active=owned(c,row['id'])
    if active['status']!='RUNNING' or active['lease_owner']!=row['lease_owner']:raise HTTPException(409,'Job is no longer active.')
    if latest['website']!=b['website']:raise HTTPException(409,'Company website changed during enrichment.')
    if crawl is not None and not crawl.pages_crawled:return {'status':'UNAVAILABLE','reason':'NO_PUBLIC_COMPANY_INFORMATION'}
    if kind=='COMPANY_ENRICH':
        data=json.loads(latest['source_tags_json'] or '{}');data['company_intelligence']=evidence(crawl,b['name']);c.execute('UPDATE businesses SET source_tags_json=?,updated_at=? WHERE id=? AND run_id IN (SELECT id FROM pipeline_runs WHERE organization_id=?)',(json.dumps(data),now(),b['id'],row['organization_id']))
        return {'status':'COMPLETE','mode':'PUBLIC_WEBSITE','pages':crawl.pages_crawled}
    from app.people.extraction import extract_people
    candidates=contacts_cache.get('candidates',[]) if cached_contacts else extract_people(crawl.all_htmls,b['name']);keys=[]
    if not cached_contacts:
        data=json.loads(latest['source_tags_json'] or '{}');data['professional_contacts']={'website':b['website'],'retrieved_at':now(),'candidates':candidates,'pages':crawl.pages_crawled}
        c.execute('UPDATE businesses SET source_tags_json=?,updated_at=? WHERE id=? AND run_id IN (SELECT id FROM pipeline_runs WHERE organization_id=?)',(json.dumps(data),now(),b['id'],row['organization_id']))
    if contact:
        candidates=[candidate for candidate in candidates if candidate['name'].casefold()==contact['name'].casefold() and (not contact['profile_url'] or candidate['profile_url']==contact['profile_url']) and (not contact['role'] or candidate['role'].casefold()==contact['role'].casefold())]
        if len(candidates)!=1:return {'status':'UNAVAILABLE','reason':'NO_UNAMBIGUOUS_PROFESSIONAL_MATCH'}
    for candidate in candidates:
        if contact and candidate['name'].casefold()!=contact['name'].casefold():continue
        try:body=Person(**candidate,confidence='MEDIUM',revision=contact['revision'] if contact else None,request_id=uuid.uuid5(uuid.NAMESPACE_URL,'public-person:'+b['prospect_id']+':'+candidate['name'].casefold()+':'+candidate['role'].casefold()))
        except ValueError:continue
        # Enrichment does not overwrite manually curated facts or a stronger verification.
        if contact:
            fields=body.model_dump();fields.update({field:contact[field] for field in ('name','role','department','seniority','job_function','work_email','phone','profile_url','confidence') if contact.get(field)});body=Person.model_validate(fields)
        saved=save(c,b['id'],body,contact['id'] if contact else None,origin='PUBLIC_COMPANY_STRUCTURED_DATA');keys.append(saved['id'])
    return {'status':'COMPLETE' if keys else 'UNAVAILABLE','reason':None if keys else 'NO_EXPLICIT_PROFESSIONAL_RELATIONSHIP_FOUND','contacts':keys,'provider':'PUBLIC_COMPANY_STRUCTURED_DATA','pages':contacts_cache.get('pages',0) if cached_contacts else crawl.pages_crawled,'mode':'CACHED' if cached_contacts else 'PUBLIC_WEBSITE'}

def execute(key,db_path=None):
    with db_session(db_path) as entry:
        with job_scope(entry,'intelligence',key):return asyncio.run(_execute(key,db_path))

async def _execute(key,db_path):
    lease=str(uuid.uuid4());deadline=time.monotonic()+240
    with db_session(db_path) as c:
        row=owned(c,key);ctx(c,True)
        expiry=(datetime.now(timezone.utc)+timedelta(seconds=300)).isoformat()
        claimed=c.execute("UPDATE intelligence_jobs SET status='RUNNING',lease_owner=?,lease_until=?,attempts=attempts+1,updated_at=? WHERE id=? AND organization_id=? AND attempts<3 AND (status='QUEUED' OR (status='RUNNING' AND lease_until<?))",(lease,expiry,now(),key,row['organization_id'],now())).rowcount
        if not claimed:return
        c.execute("UPDATE intelligence_job_items SET status='QUEUED' WHERE job_id=? AND status='PROCESSING'",(key,));c.commit();row=owned(c,key);configuration=json.loads(row['configuration_json'])
        for item in c.execute("SELECT * FROM intelligence_job_items WHERE job_id=? AND status='QUEUED' ORDER BY id",(key,)).fetchall():
            if time.monotonic()>deadline:break
            active=owned(c,key)
            if active['status']!='RUNNING' or active['lease_owner']!=lease:return
            ctx(c,True);c.execute("UPDATE intelligence_job_items SET status='PROCESSING',updated_at=? WHERE id=?",(now(),item['id']));c.commit()
            try:
                result=await asyncio.wait_for(run_item(c,row,dict(item),configuration),timeout=35)
                active=owned(c,key)
                if active['status']!='RUNNING' or active['lease_owner']!=lease:c.rollback();return
                c.execute('UPDATE intelligence_job_items SET status=?,result_json=?,error_code=NULL,updated_at=? WHERE id=?',(result.pop('status'),json.dumps(result),now(),item['id']));c.commit()
            except Exception as exc:
                c.rollback();active=owned(c,key)
                if active['status']!='RUNNING' or active['lease_owner']!=lease:return
                c.execute("UPDATE intelligence_job_items SET status='FAILED',error_code=?,updated_at=? WHERE id=?",(type(exc).__name__,now(),item['id']));c.commit()
        pending=c.execute("SELECT COUNT(*) FROM intelligence_job_items WHERE job_id=? AND status IN ('FAILED','QUEUED','PROCESSING')",(key,)).fetchone()[0]
        c.execute('UPDATE intelligence_jobs SET status=?,lease_owner=NULL,lease_until=NULL,completed_at=?,updated_at=? WHERE id=? AND organization_id=? AND lease_owner=?',('PARTIAL' if pending else 'COMPLETED',now(),now(),key,row['organization_id'],lease))
