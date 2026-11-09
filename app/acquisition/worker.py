"""Isolated optional source worker. This module never invokes an email send/tick."""
import asyncio,os,json,time,uuid,threading,hashlib,logging,traceback
from datetime import datetime,timedelta,timezone
from itertools import islice
from app.database.connection import db_session,get_connection
from app.database.migrations import verify_schema
from app.database.prospects import now
from app.acquisition import service
from app.acquisition.models import SearchIntent,ProcessingOptions,ColumnMapping,Budgets
from app.acquisition.imports import normalize_row,ImportInvalid
from app.acquisition.firecrawl import FirecrawlLeadSource,SourceUnavailable
from app.acquisition.pipeline import analyze_batch
from app.config.locations import country
from app.config.settings import get_settings

TERMS={'dentists':['dentist','dental'],'hospitality':['hotel','guest house','accommodation','motel','bed and breakfast'],'restaurant':['restaurant','bistro','cafe'],'real_estate':['estate agent','real estate','property management'],'home_services':['plumbing','electrician','roofing','home repair','cleaning service'],'auto_repair':['auto repair','car repair','mechanic'],'legal':['solicitor','law firm','attorney'],'veterinary':['veterinary','veterinarian','animal hospital']}

def request(c,jid,key,kind,budget):
    old=c.execute('SELECT status,response_json FROM acquisition_requests WHERE job_id=? AND request_key=?',(jid,key)).fetchone()
    if old:
        if old['status']=='COMPLETED':return json.loads(old['response_json'])
        raise SourceUnavailable('A previous provider attempt has an uncertain result; it will not be repeated automatically.')
    maximum={'search':budget.max_searches,'scrape':budget.max_scraped_pages,'crawl':budget.max_crawl_pages}[kind]
    used=c.execute('SELECT COUNT(*) FROM acquisition_requests WHERE job_id=? AND kind=?',(jid,kind)).fetchone()[0]
    if used>=maximum:raise SourceUnavailable('Configured '+kind+' budget exhausted.')
    if budget.max_credits is not None:
        config=json.loads(service.job(c,jid)['configuration_json'])
        if config.get('processing',{}).get('qualification_mode')!='CONTACTABLE_ONLY':raise SourceUnavailable('Credit ceilings require the bounded contactable-only request format.')
        bounds={'search':10,'scrape':1,'crawl':budget.max_crawl_pages}
        rows=c.execute("SELECT kind,credits FROM acquisition_requests WHERE job_id=? AND kind IN ('search','scrape','crawl')",(jid,)).fetchall()
        reserved=sum(r['credits'] if r['credits'] is not None else bounds[r['kind']] for r in rows)
        if reserved+bounds[kind]>budget.max_credits:raise SourceUnavailable('Configured Firecrawl credit ceiling reached; unknown or in-flight usage remains conservatively reserved.')
    c.execute("INSERT INTO acquisition_requests(job_id,request_key,kind,status,created_at) VALUES(?,?,?,'RESERVED',?)",(jid,key,kind,now()));c.commit();return None

async def provider_request(jid,key,kind,budget,produce,db_path=None):
    with db_session(db_path) as c:cached=request(c,jid,key,kind,budget)
    if cached is not None:return cached
    try:value=await produce()
    except Exception:
        with db_session(db_path) as c:c.execute("UPDATE acquisition_requests SET status='FAILED' WHERE job_id=? AND request_key=?",(jid,key))
        raise
    # Store only bounded candidate evidence needed for deterministic continuation.
    with db_session(db_path) as c:c.execute("UPDATE acquisition_requests SET status='COMPLETED',response_json=?,credits=? WHERE job_id=? AND request_key=?",(service.encoded(value),value.get('credits') if isinstance(value,dict) else None,jid,key))
    return value

def record_no_email(c,jid,url):
    prefix='No usable publicly evidenced business email; no deep analysis performed.'
    service.issue(c,jid,None,prefix,{'url':url})
    # LIKE patterns are data. A literal percent in SQL is interpreted by the
    # PostgreSQL driver when parameters are present, so bind the entire pattern.
    count=c.execute('SELECT COUNT(*) FROM acquisition_issues WHERE job_id=? AND reason LIKE ?',(jid,prefix+'%')).fetchone()[0]
    service.refresh_counts(c,jid,{'no_email':count})

async def resume_source_analysis(jid,processing,target,budget,started,db_path=None):
    """A contactable target is not proof that its saved analysis completed."""
    from app.database.repositories import BusinessRepository
    with db_session(db_path) as c:
        pending=[dict(row) for row in c.execute("SELECT a.batch_key,a.run_id FROM acquisition_batches a JOIN pipeline_runs r ON r.id=a.run_id WHERE a.job_id=? AND r.status<>'COMPLETED' ORDER BY a.run_id",(jid,)).fetchall()]
    for batch in pending:
        check_source(jid,db_path)
        remaining=budget.max_runtime_seconds-(time.monotonic()-started)
        if remaining<=5:raise SourceUnavailable('Contactable leads are preserved; remaining analysis reached its execution budget. Resume the saved checkpoint.')
        with db_session(db_path) as c:
            businesses=[BusinessRepository(c)._row_to_business(row) for row in c.execute('SELECT * FROM businesses WHERE run_id=?',(batch['run_id'],)).fetchall()]
        await analyze_batch(jid,batch['batch_key'],businesses,processing,target=min(target,len(businesses)),timeout=remaining,db_path=db_path)

async def firecrawl_job(jid,configuration,db_path=None):
    intent=SearchIntent.model_validate(configuration['intent']);budget=Budgets.model_validate(configuration.get('budgets',{}));processing=ProcessingOptions.model_validate(configuration['processing']);source=FirecrawlLeadSource();source.contactable=processing.qualification_mode=='CONTACTABLE_ONLY';budget=budget.model_copy(update={'max_crawl_pages':0}) if source.contactable else budget;started=time.monotonic();seen=set();read=0
    await resume_source_analysis(jid,processing,intent.targetQualifiedLeads,budget,started,db_path)
    from app.acquisition.search_plan import queries,family
    with db_session(db_path) as c:
        completed=[json.loads(r[0]) for r in c.execute("SELECT counts_json FROM acquisition_events WHERE job_id=? AND stage='QUERY_RESULT'",(jid,)).fetchall()]
        saved_searches={r['request_key']:json.loads(r['response_json'] or '{}') for r in c.execute("SELECT request_key,response_json FROM acquisition_requests WHERE job_id=? AND kind='search' AND status='COMPLETED'",(jid,)).fetchall()}
    completed_queries={r.get('query') for r in completed}
    read=sum(len(r.get('items',[])) for r in saved_searches.values())
    # Fully processed queries have durable result events. Preserve partial-query
    # replay so unvisited cached search hits are still available after a resume.
    pending=[(i,q) for i,q in enumerate(queries(intent,budget.max_searches)) if q not in completed_queries]
    productivity={family(r['query']):r.get('new_qualified',0)/max(1,r.get('results',0)) for r in completed if r.get('query')}
    pending.sort(key=lambda entry:(-productivity.get(family(entry[1]),0),entry[0]))
    while pending:
        index,query=pending.pop(0);query_started_qualified=0;query_businesses=0;query_emails=0
        check_source(jid,db_path)
        with db_session(db_path) as c:
            failed=c.execute("SELECT 1 FROM acquisition_requests WHERE job_id=? AND request_key=? AND status='FAILED'",(jid,'search:'+str(index))).fetchone()
        if failed:continue # An explicit resume advances without rebilling an uncertain failed request.
        if time.monotonic()-started>=budget.max_runtime_seconds:raise SourceUnavailable('Acquisition runtime budget exhausted; partial results preserved.')
        with db_session(db_path) as c:
            counts=service.refresh_counts(c,jid)
            if counts.get('qualified',0)>=intent.targetQualifiedLeads:return
            service.event(c,jid,'SEARCHING_WEB','Searching: '+query)
        query_started_qualified=counts.get('qualified',0)
        remaining=intent.targetQualifiedLeads-counts.get('qualified',0)
        if read>=budget.max_candidates and 'search:'+str(index) not in saved_searches:raise SourceUnavailable('Candidate budget exhausted; contactable shortfall recorded.')
        result=await provider_request(jid,'search:'+str(index),'search',budget,lambda:source.search(query,limit=min(50,max(10,remaining*2),budget.max_candidates-read),country_code=country(intent.countries[0]).alpha_2),db_path)
        items=result['items']
        if 'search:'+str(index) not in saved_searches:read+=len(items)
        with db_session(db_path) as c:service.event(c,jid,'FINDING_BUSINESSES','Public search results received.',{'search_results':read});service.refresh_counts(c,jid,{'search_results':read})
        batch=[]
        for hit in items:
            check_source(jid,db_path)
            url=hit.get('url','');key=hashlib.sha256(url.encode()).hexdigest()
            if not url or url in seen:continue
            seen.add(url)
            from app.acquisition.firecrawl import discovery_url_allowed
            if not discovery_url_allowed(url):
                with db_session(db_path) as c:service.issue(c,jid,None,'Directory/aggregator result excluded before paid page retrieval.',{'url':url})
                continue
            with db_session(db_path) as c:
                failed=c.execute("SELECT 1 FROM acquisition_requests WHERE job_id=? AND request_key=? AND status='FAILED'",(jid,'scrape:'+key)).fetchone()
            if failed:continue
            if len(seen)>budget.max_candidates:raise SourceUnavailable('Candidate budget exhausted; qualified shortfall recorded.')
            try:
                async def scrape_checked():
                    page=await source.scrape(url);candidate,why=source.candidate(url,page);return {'candidate':candidate,'reason':why,'credits':page.get('_credits_used')}
                result=await provider_request(jid,'scrape:'+key,'scrape',budget,scrape_checked,db_path)
                data,reason=result['candidate'],result['reason']
            except SourceUnavailable:
                if batch:await analyze_batch(jid,'query:'+str(index)+':partial',batch,processing,target=intent.targetQualifiedLeads,timeout=max(1,budget.max_runtime_seconds-(time.monotonic()-started)),db_path=db_path)
                raise
            if reason:
                with db_session(db_path) as c:service.issue(c,jid,None,reason,{'url':url})
                continue
            query_businesses+=1
            if not data.get('email'):
                from app.acquisition.enrichment import contact_page_email
                try:data=await contact_page_email(jid,data,source,budget,db_path)
                except SourceUnavailable:
                    if batch:await analyze_batch(jid,'query:'+str(index)+':partial',batch,processing,target=intent.targetQualifiedLeads,timeout=max(1,budget.max_runtime_seconds-(time.monotonic()-started)),db_path=db_path)
                    raise
            if budget.max_crawl_pages and not data.get('email'):
                from app.acquisition.enrichment import optional_contacts
                data=await optional_contacts(jid,data,source,budget,db_path)
            from app.acquisition.policy import published_email
            email=published_email(data,data.get('field_sources',{}))
            if not email:
                with db_session(db_path) as c:
                    record_no_email(c,jid,url)
                continue
            from app.enrichment.dns import check_email_dns
            _,dns_valid=await asyncio.to_thread(check_email_dns,email)
            if not dns_valid:
                with db_session(db_path) as c:service.issue(c,jid,None,'Published email domain could not be validated; no deep analysis performed.',{'url':url})
                continue
            with db_session(db_path) as c:
                blocked=c.execute("SELECT 1 FROM email_address_suppressions WHERE LOWER(address)=? AND status IN ('INVALID','TEMPORARILY_UNUSABLE')",(email,)).fetchone()
            if blocked:
                with db_session(db_path) as c:service.issue(c,jid,None,'Published email is delivery-blocked; no deep analysis performed.',{'url':url})
                continue
            from app.mail.contacted import lookup
            with db_session(db_path) as c:already=lookup(c,email)
            if already:
                with db_session(db_path) as c:service.issue(c,jid,None,'ALREADY_CONTACTED',{'url':url});service.refresh_counts(c,jid)
                continue
            query_emails+=1
            data['email']=email;data['field_sources']['email'].update(value=email,dns_validated=True,discovered_at=now())
            text=data.pop('evidence_text','');vertical=next((v for v in intent.verticals if any(term in text for term in TERMS[v])),None)
            if not vertical:
                with db_session(db_path) as c:service.issue(c,jid,None,'Business vertical was not confirmed from public page evidence.',{'url':url})
                continue
            data['vertical']=vertical
            if not data.get('city') and len(intent.cities)==1 and intent.cities[0].casefold() in text:data['city']=intent.cities[0];data['field_sources']['city']={'source':'FIRECRAWL','url':url,'verification':'OBSERVED_PUBLIC_PAGE'}
            if not data.get('country'):data['country']=intent.countries[0];data['field_sources']['country']={'source':'REVIEWED_SEARCH_CONTEXT','verification':'NOT_INDEPENDENTLY_VERIFIED'}
            try:
                b=normalize_row(data,processing,'FIRECRAWL')
                if b.country not in intent.countries:raise ImportInvalid('Business is outside the reviewed countries.')
                tags={'source_url':data['source_url'],'field_sources':data['field_sources'],'query':query}
                if intent.cities and not any(city.casefold() in (b.city or '').casefold() for city in intent.cities):tags['needs_review']='LOCATION_REQUIRES_REVIEW'
                b.source_tags=service.encoded(tags);batch.append(b)
            except (ValueError,ImportInvalid) as exc:
                with db_session(db_path) as c:service.issue(c,jid,None,str(exc),{'url':url})
            if len(batch)>=min(10,remaining):
                await analyze_batch(jid,'query:'+str(index)+':'+str(len(seen)),batch,processing,target=intent.targetQualifiedLeads,timeout=max(1,budget.max_runtime_seconds-(time.monotonic()-started)),db_path=db_path);batch=[]
                with db_session(db_path) as c:
                    current=service.refresh_counts(c,jid).get('qualified',0)
                    if current>=intent.targetQualifiedLeads:return
                    remaining=intent.targetQualifiedLeads-current
        if batch:await analyze_batch(jid,'query:'+str(index)+':tail',batch,processing,target=intent.targetQualifiedLeads,timeout=max(1,budget.max_runtime_seconds-(time.monotonic()-started)),db_path=db_path)
        with db_session(db_path) as c:
            current=service.refresh_counts(c,jid).get('qualified',0);metrics={'query':query,'results':len(items),'businesses_found':query_businesses,'emails_found':query_emails,'new_qualified':max(0,current-query_started_qualified),'email_hit_rate':query_emails/max(1,query_businesses)}
            service.event(c,jid,'QUERY_RESULT','Bounded query contactability measured.',metrics)
        productivity[family(query)]=metrics['new_qualified']/max(1,metrics['results'])
        pending.sort(key=lambda entry:(-productivity.get(family(entry[1]),0),entry[0]))
    with db_session(db_path) as c:
        counts=service.refresh_counts(c,jid)
        if counts.get('qualified',0)<intent.targetQualifiedLeads:raise SourceUnavailable('Search plan exhausted before the qualified-lead target; shortfall recorded.')

class SourceStopped(RuntimeError):pass

def check_source(jid,db_path=None):
    with db_session(db_path) as c:
        r=service.job(c,jid)
        if r['status'] in ('PAUSED','CANCELLED'):raise SourceStopped('Source processing was paused or stopped by its owner.')
        origin=json.loads(r['origin_json']);rid=origin.get('workflow_run_id')
        if rid:
            parent=c.execute('SELECT status FROM workflow_runs WHERE id=?',(rid,)).fetchone()
            if parent and parent[0] in ('PAUSED','CANCELLED'):raise SourceStopped('Parent schedule run is paused or cancelled.')

async def import_job(jid,configuration,db_path=None):
    """Complete canonical intake before analysis so failures cannot drop imports."""
    from app.acquisition.pipeline import prepare_import_batch
    from app.database.repositories import BusinessRepository
    processing=ProcessingOptions.model_validate(configuration['processing']);started=time.monotonic();budget=Budgets.model_validate(configuration.get('budgets',{}))
    with db_session(db_path) as c:r=service.job(c,jid);mapping=ColumnMapping.model_validate_json(r['mapping_json']);cursor=r['cursor'];counts=json.loads(r['counts_json'])
    if r['source_type']=='GOOGLE_SHEETS' and not r['upload_key']:
        from app.acquisition.sheets import snapshot
        with db_session(db_path) as c:await snapshot(c,r)
        with db_session(db_path) as c:r=service.job(c,jid)
    manifest=json.loads(r['manifest_json'])
    if not counts.get('_intake_complete'):
        iterator=service.source_book(r).mapped_rows(manifest['sheet'],mapping);read=valid=invalid=0;batch=[];last=cursor
        def persist(number):
            with db_session(db_path) as c:
                if batch:prepare_import_batch(c,jid,'rows:'+str(number),batch,processing)
                current=service.refresh_counts(c,jid);service.refresh_counts(c,jid,{'rows_read':current.get('rows_read',0)+read,'valid_rows':current.get('valid_rows',0)+valid,'invalid_rows':current.get('invalid_rows',0)+invalid})
                c.execute('UPDATE acquisition_jobs SET cursor=? WHERE id=?',(number,jid))
        for number,data in iterator:
            check_source(jid,db_path)
            if number<=cursor:continue
            read+=1;last=number
            try:
                b=normalize_row(data,processing,r['source_type']);origin=json.loads(r['origin_json'])
                tags={'provided_industry':data.get('vertical'),'row_number':number,'contact_person':data.get('contact_name') or None,'source_url':origin.get('spreadsheet_url'),'processing_policy':'TRUSTED_IMPORT','field_sources':{k:{'source':r['source_type'],'file':origin.get('filename'),'sheet':manifest['sheet'],'row':number,'column':mapping.model_dump().get(k),'verification':'SOURCE_ROW'} for k,v in data.items() if v}}
                if data.get('email'):tags['field_sources']['email'].update(verification='OWNER_PROVIDED',value=b.public_email)
                b.source_tags=service.encoded(tags);batch.append(b);valid+=1
            except (ValueError,ImportInvalid) as exc:
                invalid+=1
                with db_session(db_path) as c:service.issue(c,jid,number,str(exc),data)
            if read>=20:
                persist(number);batch=[];read=valid=invalid=0
                if time.monotonic()-started>budget.max_runtime_seconds-30:raise SourceUnavailable('Import intake budget reached. Qualified rows retained; resume from the saved row checkpoint.')
        if read:persist(last)
        with db_session(db_path) as c:
            counts=service.refresh_counts(c,jid,{'_intake_complete':1});c.execute('UPDATE scan_campaigns SET target_total=? WHERE id=?',(counts.get('qualified',0),r['campaign_id']))
            service.event(c,jid,'INTAKE_COMPLETE','Canonical intake complete. Valid unique rows are qualified; analysis and send eligibility remain separate.',counts)
    with db_session(db_path) as c:batches=[dict(x) for x in c.execute('SELECT batch_key,run_id FROM acquisition_batches WHERE job_id=? ORDER BY run_id',(jid,)).fetchall()]
    failures=[]
    for item in batches:
        check_source(jid,db_path)
        with db_session(db_path) as c:
            run=c.execute('SELECT status FROM pipeline_runs WHERE id=?',(item['run_id'],)).fetchone()
            if run['status']=='COMPLETED':continue
            businesses=[BusinessRepository(c)._row_to_business(row) for row in c.execute('SELECT * FROM businesses WHERE run_id=?',(item['run_id'],)).fetchall()]
        remaining=budget.max_runtime_seconds-(time.monotonic()-started)
        if remaining<=5:raise SourceUnavailable('Import analysis budget reached. All ingested leads remain qualified; resume pending analysis.')
        try:await analyze_batch(jid,item['batch_key'],businesses,processing,target=len(businesses),timeout=remaining,db_path=db_path)
        except (RuntimeError,ValueError):failures.append(item['run_id'])
    if failures:raise SourceUnavailable('Imported leads remain qualified. Some website analyses failed; retry pending analysis from its checkpoint.')

async def process(jid,db_path=None):
    with db_session(db_path) as c:r=service.job(c,jid);configuration=json.loads(r['configuration_json']);service.event(c,jid,'NORMALIZING','Source processing started; existing acquisition and email workers are independent.')
    budget=Budgets.model_validate(configuration.get('budgets',{}))
    task=firecrawl_job(jid,configuration,db_path) if r['source_type']=='FIRECRAWL' else import_job(jid,configuration,db_path)
    try:await asyncio.wait_for(task,timeout=budget.max_runtime_seconds)
    except asyncio.TimeoutError:
        raise SourceUnavailable('Acquisition execution runtime budget reached. Partial results preserved; retry from the saved checkpoint.') from None

def execute(jid,db_path=None):
    from app.platform.context import job_scope
    with db_session(db_path) as scope_conn:
        verify_schema(scope_conn)
        with job_scope(scope_conn,'acquisition',jid):
            return _execute_owned(jid,db_path)

def _execute_owned(jid,db_path=None):
    owner=str(uuid.uuid4());stop=threading.Event();lock=get_connection(db_path,session_bound=True);claimed=False
    try:
        verify_schema(lock)
        from app.acquisition.config import require
        with db_session(db_path) as c:
            source_job=service.job(c,jid)
            from fastapi import HTTPException
            try:
                require('firecrawl' if source_job['source_type']=='FIRECRAWL' else 'import',c)
                if source_job['source_type']=='GOOGLE_SHEETS':require('sheets',c)
            except HTTPException:
                c.execute("UPDATE acquisition_jobs SET status='DEGRADED',error_code='ACQUISITION_FEATURE_DISABLED',error_message='Source is disabled. Enable it before explicitly retrying.',execution_name=NULL,updated_at=? WHERE id=? AND status='QUEUED'",(now(),jid))
                return
        if getattr(lock,'backend',None)=='postgres':
            # Separate global acquisition capacity and job-id lock; never take the Overture dispatcher lock.
            if not lock.execute('SELECT pg_try_advisory_lock(691944913)').fetchone()[0]:
                with db_session(db_path) as c:c.execute("UPDATE acquisition_jobs SET status='DEGRADED',error_code='ACQUISITION_CAPACITY_BUSY',execution_name=NULL WHERE id=? AND status='QUEUED'",(jid,))
                lock.commit();return
            lock.commit()
        with db_session(db_path) as c:
            r=service.job(c,jid)
            if r['status'] not in ('QUEUED','FAILED','DEGRADED') or r['lease_until'] and r['lease_until']>now():return
            expiry=(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat();c.execute("UPDATE acquisition_jobs SET status='RUNNING',lease_owner=?,lease_until=?,updated_at=? WHERE id=?",(owner,expiry,now(),jid));claimed=True
        def heartbeat():
            while not stop.wait(25):
                try:
                    expiry=(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat()
                    with db_session(db_path) as c:
                        c.execute('UPDATE acquisition_jobs SET lease_until=? WHERE id=? AND lease_owner=?',(expiry,jid,owner))
                except Exception:pass
        threading.Thread(target=heartbeat,daemon=True).start()
        diagnostic=None
        try:asyncio.run(process(jid,db_path));status='COMPLETED';code=None;message=None
        except Exception as exc:
            from app.acquisition.sheets import SheetsUnavailable
            diagnostic={'error_type':type(exc).__name__,'frames':[f'{frame.name}:{frame.lineno}' for frame in traceback.extract_tb(exc.__traceback__)[-4:]]}
            # No exception text, request bodies, contacts, credentials or SQL
            # parameters enter logs. The type and code locations are sufficient
            # to diagnose the preserved checkpoint.
            logging.getLogger(__name__).error('Acquisition checkpoint failed: job=%s diagnostic=%s',jid,json.dumps(diagnostic))
            status='DEGRADED';code='SOURCE_UNAVAILABLE' if isinstance(exc,(SourceUnavailable,SheetsUnavailable)) else 'IMPORT_INVALID' if isinstance(exc,ImportInvalid) else 'ACQUISITION_FAILED'
            message=str(exc)[:500] if isinstance(exc,(SourceUnavailable,SheetsUnavailable,ImportInvalid)) else 'Acquisition did not finish; inspect source issues and retry from its checkpoint.'
        with db_session(db_path) as c:
            r=service.job(c,jid);counts=service.refresh_counts(c,jid);intent=json.loads(r['configuration_json']).get('intent',{});counts['shortfall']=max(0,intent.get('targetQualifiedLeads',0)-counts.get('qualified',0));service.refresh_counts(c,jid,counts)
            if not counts.get('candidates',0) and status=='DEGRADED':status='FAILED'
            if r['status'] in ('PAUSED','CANCELLED'):status=r['status'];code=None;message=None
            c.execute('UPDATE acquisition_jobs SET status=?,error_code=?,error_message=?,finished_at=?,updated_at=? WHERE id=?',(status,code,message,now(),now(),jid))
            if r['campaign_id']:c.execute('UPDATE scan_campaigns SET status=?,completed_at=? WHERE id=?',(status if status in ('PAUSED','CANCELLED') else 'COMPLETED' if status=='COMPLETED' else 'NEEDS_REVIEW' if counts.get('qualified',0)>0 else 'FAILED',now(),r['campaign_id']))
            if diagnostic and status not in ('PAUSED','CANCELLED'):service.event(c,jid,'ERROR_DIAGNOSTIC','Checkpoint failed: '+diagnostic['error_type']+'; code locations '+', '.join(diagnostic['frames']),diagnostic)
            service.event(c,jid,status,'Acquisition completed.' if status=='COMPLETED' else 'Partial results preserved. Inspect issues and retry explicitly; existing scans and outreach are unaffected.',counts)
    finally:
        stop.set()
        if claimed:
            with db_session(db_path) as c:
                c.execute('UPDATE acquisition_jobs SET lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?',(jid,owner));c.execute('UPDATE pipeline_runs SET lease_owner=NULL,lease_expires_at=NULL WHERE lease_owner=?',(owner,))
        lock.close()
if __name__=='__main__':
    if os.environ.get('ACQUISITION_PROVIDER_CHECK')=='vertex':
        from scripts.vertex_runtime_smoke import smoke
        asyncio.run(smoke());raise SystemExit(0)
    if os.environ.get('ACQUISITION_PROVIDER_CHECK')=='gemini':
        from app.acquisition.ai import GeminiInstructionProvider
        try:
            result=asyncio.run(GeminiInstructionProvider().parse_lead_search_intent('Find 5 dentists in Bristol UK with website and SEO opportunities.'))
            passed=result.targetQualifiedLeads==5 and result.verticals==['dentists'] and result.cities==['Bristol']
            print(json.dumps({'provider_check':'gemini','passed':passed,'intent':result.model_dump(),'no_database_leads_or_emails':True}),flush=True)
            raise SystemExit(0 if passed else 1)
        except Exception as exc:
            print(json.dumps({'provider_check':'gemini','passed':False,'error_type':type(exc).__name__,'no_database_leads_or_emails':True}),flush=True)
            raise SystemExit(1)
    else:execute(str(uuid.UUID(os.environ['LEADENGINE_ACQUISITION_JOB_ID'])))
