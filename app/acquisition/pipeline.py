"""A discovery dependency for the shared PipelineRunner, never a parallel analyzer."""
import json,uuid,asyncio,time
from collections import Counter
from app.config.markets import MarketInfo,BoundingBox
from app.config.verticals import get_vertical_manager
from app.database.connection import db_session
from app.database.models import PipelineRun
from app.database.repositories import PipelineRunRepository,BusinessRepository
from app.database.prospects import ProspectRepository,identity_keys,now
from app.normalization.dedupe import deduplicate_businesses
from app.qualification.vertical_validator import VerticalValidator,VerticalValidationStatus
from app.acquisition.service import event,job,refresh_counts,issue,encoded
from app.acquisition.policy import policy

class CandidateCoordinator:
    def __init__(self,businesses,processing,source_policy=None):self.businesses=businesses;self.processing=processing;self.source_policy=source_policy;self.vertical_mgr=get_vertical_manager()
    def resolve_market(self,value):
        # This is a global input-batch extent, not an inferred company location.
        return MarketInfo(query=value,city='Acquisition selection',state='',country=self.processing.default_country,country_code='',bbox=BoundingBox(min_lat=-90,min_lon=-180,max_lat=90,max_lon=180),center_lat=0,center_lon=0,cached=True)
    def discover(self,market_str,vertical_str,target_leads=50,include_chains=False):
        unique,duplicates=deduplicate_businesses(self.businesses);rejected=[];candidates=[];frequencies=Counter(b.domain for b in unique if b.domain)
        for b in duplicates:b.is_duplicate=True;b.is_rejected=True;b.rejection_reason='DUPLICATE';b.processing_status='REJECTED';rejected.append(b)
        for b in unique:
            tags=json.loads(b.source_tags or '{}')
            if self.source_policy and self.source_policy.mode.value=='EMAIL_CONTACTABLE_DISCOVERY':
                from app.acquisition.policy import published_email
                if not b.website or not published_email(b,tags.get('field_sources',{})):continue
            if self.source_policy and self.source_policy.trusted_import:
                b.processing_status='QUALIFIED';b.is_rejected=False;b.rejection_reason=None
                candidates.append(b);continue
            if self.source_policy and not self.source_policy.business_fit_gate:
                if tags.get('needs_review'):b.is_rejected=True;b.processing_status='REJECTED';b.rejection_reason=tags['needs_review'];rejected.append(b)
                else:b.processing_status='NORMALIZED';b.is_rejected=False;b.rejection_reason=None;candidates.append(b)
                continue
            status,reason,confidence=VerticalValidator.validate(b);b.vertical_validation_status=status.value;b.vertical_validation_reason=reason;b.vertical_validation_confidence=confidence
            chain,why,certainty=self.vertical_mgr.check_chain(b.name,b.domain,b.vertical,frequencies.get(b.domain,1));b.is_chain=chain;b.chain_reason=why;b.chain_confidence=certainty
            review=tags.get('needs_review')
            if review or status!=VerticalValidationStatus.VALID or chain and not include_chains:
                b.is_rejected=True;b.processing_status='REJECTED';b.rejection_reason=review or 'CHAIN' if chain and not include_chains else review or ('VERTICAL_MISMATCH' if status==VerticalValidationStatus.INVALID else 'UNCERTAIN_NICHE');rejected.append(b)
            else:b.processing_status='NORMALIZED';candidates.append(b)
        return self.resolve_market(market_str),self.vertical_mgr.resolve_vertical(vertical_str),candidates,rejected

def inherit_existing(c,b,tags,*,organization):
    if not organization:
        raise ValueError('Existing lead reuse requires a workspace context')
    keys=identity_keys(b,organization)+identity_keys(b)
    matched={r[0] for r in c.execute('SELECT i.prospect_id FROM business_identities i JOIN prospects p ON p.id=i.prospect_id WHERE p.organization_id=? AND i.identity_key IN ('+','.join('?' for _ in keys)+')',[organization]+[x[0] for x in keys]).fetchall()}
    if len(matched)!=1:return
    pid=next(iter(matched));row=c.execute('SELECT website,phone,id FROM businesses WHERE prospect_id=? AND is_rejected=0 ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    if row:
        for field in ('website','phone'):
            if not getattr(b,field) and row[field]:setattr(b,field,row[field]);tags.setdefault('field_sources',{})[field]={'source':'EXISTING_MASTER','business_id':row['id']}
    if not b.public_email:
        row=c.execute("SELECT x.contact_value,x.source_url FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id=? AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 ORDER BY x.id DESC LIMIT 1",(pid,)).fetchone()
        if row:b.public_email=row['contact_value'];tags.setdefault('field_sources',{})['email']={'source':'EXISTING_MASTER','url':row['source_url']}

def finalize_evidence(c,jid,run_id):
    r=job(c,jid);cid=r['campaign_id'];actor=r['owner']
    from fastapi import HTTPException
    owned=c.execute('SELECT 1 FROM pipeline_runs WHERE id=? AND organization_id=? AND campaign_id=?',(run_id,r['organization_id'],cid)).fetchone()
    if not owned:raise HTTPException(404,'Acquisition scan not found in this workspace.')
    for row in c.execute('SELECT * FROM businesses WHERE run_id=?',(run_id,)).fetchall():
        b=BusinessRepository(c)._row_to_business(row);pid=row['prospect_id'];tags=json.loads(b.source_tags or '{}')
        contactable_only=json.loads(r['configuration_json']).get('processing',{}).get('qualification_mode')=='CONTACTABLE_ONLY'
        if contactable_only and b.processing_status!='QUALIFIED':continue
        if not pid and not b.is_duplicate:
            try:pid=ProspectRepository(c).observe(b,cid,actor,organization=r['organization_id'])
            except ValueError:continue
        if not pid:continue
        from app.sales.service import prospect_org
        prospect_org(c,pid,r['organization_id'])
        prior=c.execute('SELECT first_campaign_id FROM prospects WHERE id=?',(pid,)).fetchone();existing=not prior or prior[0]!=cid
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,'source:'+str(b.id)+':'+r['source_type']))
        mode=policy(r['source_type']);fields=dict(tags.get('field_sources',{}))
        measured=c.execute('SELECT reachable FROM website_profiles WHERE business_id=?',(b.id,)).fetchone()
        run_state=c.execute('SELECT status FROM pipeline_runs WHERE id=?',(run_id,)).fetchone()[0]
        analysis='DISABLED' if json.loads(r['configuration_json']).get('processing',{}).get('qualification_mode')=='CONTACTABLE_ONLY' else 'NOT_AVAILABLE' if not b.website else 'COMPLETE' if measured and measured['reachable'] and run_state=='COMPLETED' else 'PENDING' if run_state in ('RUNNING','QUEUED') else 'PARTIAL' if measured and measured['reachable'] else 'FAILED'
        fields['_processing']={'policy':mode.mode.value,'qualification':'QUALIFIED_IMPORTED' if mode.trusted_import and b.processing_status=='QUALIFIED' else b.processing_status,'analysis_status':'EXCLUDED_FROM_LEAD_ENGINE','company_information_status':tags.get('company_intelligence',{}).get('status','NOT_AVAILABLE')}
        c.execute('INSERT INTO lead_source_evidence(id,prospect_id,business_id,campaign_id,source_type,source_url,field_sources_json,was_existing,observed_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(business_id,source_type) DO UPDATE SET field_sources_json=excluded.field_sources_json WHERE lead_source_evidence.organization_id=excluded.organization_id',(key,pid,b.id,cid,r['source_type'],tags.get('source_url'),encoded(fields),int(existing),b.created_at or now(),r['organization_id']))
        if mode.mode.value=='EMAIL_CONTACTABLE_DISCOVERY':
            from app.acquisition.policy import published_email
            email=published_email(b,fields);proof=fields.get('email') or {}
            if email and proof.get('dns_validated') is True:
                from app.database.models import Contact
                from app.database.repositories import ContactRepository
                if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND contact_value=? AND source_type='FIRECRAWL'",(b.id,email)).fetchone():
                    # Public source evidence survives even when the later plain
                    # HTML crawler cannot rediscover a rendered/contact-page email.
                    ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=email,source_type='FIRECRAWL',source_url=proof['url'],is_public_business_contact=True,is_valid=True,confidence=0.8))
        if mode.trusted_import and b.public_email and (fields.get('email') or {}).get('verification')=='OWNER_PROVIDED':
            from app.database.models import Contact
            from app.database.repositories import ContactRepository
            if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND contact_value=? AND source_type='OWNER_IMPORT'",(b.id,b.public_email)).fetchone():
                ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=b.public_email,source_type='OWNER_IMPORT',source_url=tags.get('source_url') or 'import://'+jid+'/row/'+str(tags.get('row_number','unknown')),is_public_business_contact=False,is_valid=True,confidence=1.0))

        person=tags.get('contact_person')
        if isinstance(person,str) and 1<len(person.strip())<=150:
            person_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'import-person:'+str(b.id)+':'+person))
            source=tags.get('source_url') or 'import://'+jid+'/row/'+str(tags.get('row_number','unknown'))
            c.execute("INSERT INTO contact_people(id,prospect_id,name,confidence,source_url,created_at,created_by,organization_id) VALUES(?,?,?,'UNKNOWN',?,?,?,?) ON CONFLICT(id) DO NOTHING",(person_id,pid,person.strip(),source,now(),actor,r['organization_id']))
        if b.is_rejected and b.rejection_reason not in ('DUPLICATE','CHAIN'):
            rid=str(uuid.uuid5(uuid.NAMESPACE_URL,'acquisition-review:'+str(b.id)))
            c.execute("INSERT INTO review_cases(id,prospect_id,business_id,campaign_id,reason,evidence_json,created_at,organization_id) VALUES(?,?,?,?,'Website ownership uncertainty',?,?,?) ON CONFLICT(id) DO NOTHING",(rid,pid,b.id,cid,encoded({'source':r['source_type'],'reason':b.rejection_reason,'row':tags.get('row_number')}),now(),r['organization_id']))
    if not policy(r['source_type']).opportunity_gate:
        c.execute("UPDATE pipeline_runs SET qualified=(SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE run_id=? AND processing_status='QUALIFIED') WHERE id=?",(run_id,run_id))
    from app.automation.service import reconcile
    reconcile(c)
    refresh_counts(c,jid)

def ensure_batch(c,jid,batch_key,businesses,processing,target):
    r=job(c,jid);cid=r['campaign_id'];options=json.loads(r['configuration_json'])
    prior=c.execute('SELECT run_id FROM acquisition_batches WHERE job_id=? AND batch_key=?',(jid,batch_key)).fetchone()
    if prior:return prior['run_id']
    for b in businesses:
        tags=json.loads(b.source_tags or '{}');inherit_existing(c,b,tags,organization=r['organization_id'])
        from app.normalization.businesses import normalize_business
        normalize_business(b);b.source_tags=encoded(tags)
    campaign=json.loads(c.execute('SELECT configuration_json FROM scan_campaigns WHERE id=?',(cid,)).fetchone()[0])
    from app.workflows.history import settings as snapshot
    frozen=snapshot(c,cid)['settings'];mode=policy(r['source_type'])
    config={**campaign,'request_id':cid,'created_by':r['owner'],'quality':'balanced','results':'include_previous','target':max(1,min(1000,target)),'source_type':r['source_type'],'processing_policy':mode.mode.value,'acquisition_job_id':jid,'lighthouse_enabled':False,'lighthouse_budget':0,'analysis_mode':'INCREMENTAL','opportunities':campaign['opportunities'],'auditing':frozen.get('auditing',{}),'crawler':frozen.get('crawler',{}),'social':frozen.get('social',{})}
    from app.prospecting.policy import configuration as prospecting_configuration
    config.update(icp_id=options.get('icp_id'),icp_snapshot=options.get('icp_snapshot'))
    config=prospecting_configuration(config)
    market=(processing.default_city+', ' if processing.default_city else '')+processing.default_country
    run=PipelineRun(market=market,vertical=businesses[0].vertical if businesses else processing.default_vertical,target=config['target'],status='RUNNING',run_configuration=config)
    rid=PipelineRunRepository(c).create(run,organization=r['organization_id']);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,rid))
    c.execute('INSERT INTO acquisition_batches(job_id,batch_key,run_id) VALUES(?,?,?)',(jid,batch_key,rid))
    return rid


def prepare_import_batch(c,jid,batch_key,businesses,processing):
    """Canonical ingestion first; no network or discovery is allowed here."""
    r=job(c,jid);verticals=list(dict.fromkeys(b.vertical for b in businesses));prepared=[]
    for vertical in verticals:
        group=[b for b in businesses if b.vertical==vertical];key=batch_key+':'+vertical if len(verticals)>1 else batch_key
        rid=ensure_batch(c,jid,key,group,processing,len(group));prepared.append((key,rid))
        if c.execute('SELECT 1 FROM businesses WHERE run_id=? LIMIT 1',(rid,)).fetchone():continue
        coordinator=CandidateCoordinator(group,processing,policy(r['source_type']))
        _,_,unique,duplicates=coordinator.discover('',vertical,len(group))
        for b in unique+duplicates:
            b.run_id=rid;BusinessRepository(c).insert(b)
            if b.is_duplicate:continue
            if processing.qualification_mode=='CONTACTABLE_ONLY':
                from app.qualification.contactable import accept
                fields=json.loads(b.source_tags or '{}').get('field_sources',{});reason=accept(c,b,r['campaign_id'],r['source_type'],fields.get('email',{}))
                if reason!='QUALIFIED':issue(c,jid,None,reason,{'row':json.loads(b.source_tags or '{}').get('row_number')})
                continue
            try:ProspectRepository(c).observe(b,r['campaign_id'],r['owner'],organization=r['organization_id'])
            except ValueError:
                b.is_rejected=True;b.processing_status='REJECTED';b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED';BusinessRepository(c).update(b)
        finalize_evidence(c,jid,rid)
        event(c,jid,'QUALIFIED_IMPORTED','Valid imported rows are qualified before analysis; duplicates use existing canonical identity.',{'scan_run_id':rid,'qualified_imported':c.execute("SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE run_id=? AND processing_status='QUALIFIED'",(rid,)).fetchone()[0]})
    return prepared


async def analyze_batch(jid,batch_key,businesses,processing,*,target=50,timeout=None,db_path=None):
    from app.pipeline.runner import PipelineRunner
    with db_session(db_path) as c:r=job(c,jid)
    mode=policy(r['source_type']);verticals=list(dict.fromkeys(b.vertical for b in businesses))
    if mode.trusted_import:
        with db_session(db_path) as c:prepared=prepare_import_batch(c,jid,batch_key,businesses,processing)
        if len(prepared)>1:
            deadline=time.monotonic()+timeout if timeout else None;result=None
            for key,rid in prepared:
                with db_session(db_path) as c:group=[BusinessRepository(c)._row_to_business(row) for row in c.execute('SELECT * FROM businesses WHERE run_id=?',(rid,)).fetchall()]
                result=await analyze_batch(jid,key,group,processing,target=len(group),timeout=max(0.001,deadline-time.monotonic()) if deadline else None,db_path=db_path)
            return result
    elif len(verticals)>1:
        deadline=time.monotonic()+timeout if timeout else None;result=None
        for vertical in verticals:
            group=[b for b in businesses if b.vertical==vertical]
            result=await analyze_batch(jid,batch_key+':'+vertical,group,processing,target=min(target,len(group)),timeout=max(0.001,deadline-time.monotonic()) if deadline else None,db_path=db_path)
        return result
    with db_session(db_path) as c:
        rid=ensure_batch(c,jid,batch_key,businesses,processing,target);run=PipelineRunRepository(c).get_by_id(rid)
        if run.status=='COMPLETED':finalize_evidence(c,jid,rid);return rid
        c.execute('UPDATE pipeline_runs SET cancellation_requested=0 WHERE id=?',(rid,))
        if mode.trusted_import and not any(b.website for b in businesses):
            c.execute("UPDATE pipeline_runs SET status='COMPLETED',finished_at=?,websites_processed=0,raw_found=(SELECT COUNT(*) FROM businesses WHERE run_id=?) WHERE id=?",(now(),rid,rid))
            finalize_evidence(c,jid,rid);event(c,jid,'ANALYSIS_NOT_AVAILABLE','No website supplied. Imported qualification retained; no website facts or scores invented.',{'scan_run_id':rid});return rid
        c.execute("UPDATE scan_campaigns SET status='RUNNING' WHERE id=?",(r['campaign_id'],));event(c,jid,'ANALYZING','Lightweight company information and contact enrichment started; no website assessments.',{'batch_candidates':len(businesses),'scan_run_id':rid})
    coordinator=CandidateCoordinator(businesses,processing,mode)
    with db_session(db_path) as c:run=PipelineRunRepository(c).get_by_id(rid)
    runner=PipelineRunner(db_path=db_path,discovery_coordinator=coordinator,execution_limits={'crawl_concurrency':2,'http_concurrency':5})
    task=runner.run(run.market,run.vertical,run.target,run_id=rid,enable_lighthouse=False,run_configuration=run.run_configuration)
    try:result=await asyncio.wait_for(task,timeout=timeout) if timeout else await task
    finally:
        with db_session(db_path) as c:
            finalize_evidence(c,jid,rid);c.execute('UPDATE pipeline_runs SET lease_owner=NULL,lease_expires_at=NULL WHERE id=?',(rid,))
            event(c,jid,'QUALIFICATION','Source qualification retained independently of analysis outcome.',refresh_counts(c,jid))
    if result.status!='COMPLETED':
        if result.status=='CANCELLED' and timeout is not None:
            from app.acquisition.firecrawl import SourceUnavailable
            raise SourceUnavailable('Analysis reached its bounded execution limit. Source qualification and completed checkpoints are preserved; resume remaining analysis.')
        raise RuntimeError('SHARED_PIPELINE_'+result.status)
    return rid
