"""Schedule adapter dispatches only the explicitly selected acquisition source."""
import json,uuid
from fastapi import HTTPException
from app.acquisition.config import require
from app.acquisition.models import SearchIntent,ProcessingOptions,Budgets
from app.acquisition import service
from app.acquisition.dispatch import launch
from app.database.prospects import now

async def advance(c,run,options):
    rid=run['id']
    try:
        require('ai',c);require('firecrawl',c)
        intent=SearchIntent.model_validate(options.get('firecrawl_intent'))
        if not options.get('firecrawl_reviewed') or intent.targetQualifiedLeads!=options['target']:raise ValueError('Reviewed contactable target is missing or changed.')
    except (HTTPException,ValueError):
        c.execute("UPDATE workflow_runs SET status='NEEDS_REVIEW',error='AI + Firecrawl is disabled or its reviewed plan needs attention. No Maps fallback was started.' WHERE id=?",(rid,));return
    job=c.execute('SELECT * FROM acquisition_jobs WHERE campaign_id=?',(rid,)).fetchone()
    if not job:
        processing=ProcessingOptions(qualification_mode='CONTACTABLE_ONLY' if options.get('qualification_mode')=='CONTACTABLE_ONLY' else 'ANALYZED',analyze_websites=True,analyze_seo=True,analyze_security=True,default_country=intent.countries[0],default_city=intent.cities[0] if len(intent.cities)==1 else '',default_vertical=intent.verticals[0],lighthouse=False)
        from app.prospecting.criteria import SearchCriteria
        intent=intent.model_copy(update={'search_criteria':SearchCriteria.model_validate(options.get('search_criteria',intent.search_criteria.model_dump()))})
        configuration={'icp_id':options.get('icp_id'),'icp_snapshot':options.get('icp_snapshot'),'intent':intent.model_dump(),'processing':processing.model_dump(),'budgets':Budgets.model_validate(options.get('acquisition_budgets',{})).model_dump()}
        origin={'workflow_run_id':rid,'schedule_id':run['schedule_id'],'original_prompt':options['ai_prompt'],'interpretation_mode':'AI','queries':intent.queries}
        job=service.create_job(c,'FIRECRAWL',run['created_by'],str(uuid.uuid5(uuid.NAMESPACE_URL,rid+':firecrawl')),configuration,origin)
        c.execute('UPDATE acquisition_jobs SET campaign_id=? WHERE id=?',(rid,job['id']))
        c.execute("UPDATE scan_campaigns SET source_type='FIRECRAWL',source_metadata=?,original_prompt=? WHERE id=?",(service.encoded({'acquisition_job_id':job['id'],**origin}),options['ai_prompt'],rid))
        service.event(c,job['id'],'SCHEDULE_SOURCE','Reviewed Firecrawl source selected. The Maps worker will not be invoked.')
        c.commit();await launch(job['id']);return
    counts=json.loads(job['counts_json']);c.execute('UPDATE workflow_runs SET result_count=? WHERE id=?',(counts.get('qualified',0),rid))
    if job['status'] in ('QUEUED','RUNNING'):return
    if job['status']=='PAUSED':c.execute("UPDATE workflow_runs SET status='PAUSED',error='Source acquisition paused.' WHERE id=?",(rid,));return
    if job['status']=='CANCELLED':state='CANCELLED'
    elif job['status']=='COMPLETED' or job['status']=='DEGRADED' and counts.get('qualified',0)>0:state='COMPLETED'
    else:state='NEEDS_REVIEW'
    message=job['error_message'] or (f"Contactable target shortfall: {counts.get('shortfall',0)}." if counts.get('shortfall') else None)
    c.execute('UPDATE workflow_runs SET status=?,result_count=?,error=?,completed_at=? WHERE id=?',(state,counts.get('qualified',0),message,now() if state in ('COMPLETED','CANCELLED') else None,rid))

async def control(c,run,action):
    """Pause/stop the source checkpoint, never the legacy Maps worker."""
    from app.workflows.controls import require_unpaused
    rid=run['id'];job=c.execute('SELECT * FROM acquisition_jobs WHERE campaign_id=?',(rid,)).fetchone()
    if action=='resume':
        require_unpaused(c,'scan')
        if run['status'] not in ('PAUSED','NEEDS_REVIEW'):raise HTTPException(409,'Run is not paused.')
        if job and job['lease_owner'] and job['lease_until'] and job['lease_until']>now():raise HTTPException(409,'The source worker is finishing its current bounded operation. Retry after its lease is released.')
        if job:
            c.execute("UPDATE acquisition_jobs SET status='QUEUED',error_code=NULL,error_message=NULL,finished_at=NULL,execution_name=NULL WHERE id=?",(job['id'],))
        c.execute("UPDATE workflow_runs SET status='RUNNING',error=NULL WHERE id=?",(rid,));c.commit()
        if job:await launch(job['id'])
        else:await advance(c,run,json.loads(run['configuration_json']))
    else:
        status='PAUSED' if action=='pause' else 'CANCELLED'
        c.execute('UPDATE workflow_runs SET status=?,completed_at=? WHERE id=?',(status,None if action=='pause' else now(),rid))
        if job:
            c.execute('UPDATE acquisition_jobs SET status=?,updated_at=? WHERE id=?',(status,now(),job['id']))
            service.event(c,job['id'],status,'Owner paused or stopped this source. Completed leads and request checkpoints are preserved.')
        c.commit()
