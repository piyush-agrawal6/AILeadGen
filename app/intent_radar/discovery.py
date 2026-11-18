import asyncio, hashlib, json, uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.workflows.service import lock
from app.intent_radar import service, models, providers, connectors
from app.intent_radar.permissions import context
from app.intent_radar.classification import classify
FETCH_TIMEOUT_SECONDS=28

class ExecutionInvalidated(RuntimeError):
    """An old lease or monitor configuration cannot authorize source results."""

def create(c, body, *, scheduled=False):
    ctx=context(c,True); lock(c)
    connectors.validate(c,body.configuration)
    config=body.configuration.model_dump(mode='json')
    if body.monitor_id:
        monitor=service.get(c,'monitors',str(body.monitor_id))
        if monitor['status']!='Active':raise HTTPException(409,'Activate this monitor before running a check.')
        if monitor['configuration']!=config:raise HTTPException(409,'The monitor changed; reload its saved criteria before running.')
    parent_id=str(body.parent_discovery_id) if getattr(body,'parent_discovery_id',None) else None
    if parent_id:
        parent_row=c.execute('SELECT id FROM intent_discoveries WHERE organization_id=? AND id=?',(ctx.organization_id,parent_id)).fetchone()
        if not parent_row:raise HTTPException(404,'Parent discovery run not found.')
    key=str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id+':intent-search:'+str(body.request_id)))
    old=c.execute('SELECT * FROM intent_discoveries WHERE id=? AND organization_id=?',(key,ctx.organization_id)).fetchone()
    encoded=json.dumps(config,sort_keys=True)
    if old:
        if old['configuration_json']!=encoded or old['monitor_id']!=(str(body.monitor_id) if body.monitor_id else None):raise HTTPException(409,'Search request ID belongs to different criteria.')
    else:
        day=datetime.now(timezone.utc).date().isoformat();settings=get_settings()
        used=c.execute('SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=? AND created_at>=?',(ctx.organization_id,day)).fetchone()[0]
        total=c.execute('SELECT COUNT(*) FROM intent_discoveries WHERE created_at>=?',(day,)).fetchone()[0]
        if used>=settings.intent_radar_daily_searches or total>=settings.intent_radar_global_daily_searches:raise HTTPException(429,'Intent Radar daily search capacity is exhausted. Stored signals remain available.')
        from app.billing.usage import reserve
        from app.billing.access_periods import managed
        reserve(c,{'searches':1,**({'monitor_executions':1} if body.monitor_id and (scheduled or not managed(c,ctx.organization_id)) else {})},key)
        from app.billing.commercial_usage import settle
        if get_settings().payu_billing_enabled or get_settings().heysow_access_periods_enabled:settle(c,key)
        c.execute('INSERT INTO intent_discoveries(id,organization_id,created_by,monitor_id,monitor_revision,configuration_json,created_at) VALUES(?,?,?,?,?,?,?)',(key,ctx.organization_id,ctx.actor,str(body.monitor_id) if body.monitor_id else None,monitor['revision'] if body.monitor_id else None,encoded,now()))
        from app.intent_radar import discovery_workspace
        discovery_workspace.record_run_metadata(
            c,
            organization_id=ctx.organization_id,
            discovery_id=key,
            configuration=config,
            title=getattr(body,'title','') or '',
            original_prompt=getattr(body,'original_prompt','') or '',
            search_mode='monitor' if body.monitor_id else (getattr(body,'search_mode','advanced') or 'advanced'),
            parent_discovery_id=parent_id,
            strategy=body.strategy.model_dump(mode='json') if getattr(body,'strategy',None) else None,
        )
    from app.intelligence import jobs
    result=jobs.create(c,jobs.Start(kind='INTENT_DISCOVER',resource_ids=[key],request_id=body.request_id,reuse_days=0))
    result['discovery_id']=key
    if body.monitor_id:c.execute('UPDATE intent_monitors SET last_job_id=? WHERE id=? AND organization_id=?',(result['id'],str(body.monitor_id),ctx.organization_id))
    service.audit(c,'DISCOVERY_REQUESTED',key)
    return result

def fence(c,discovery,job_id=None,lease_owner=None):
    from app.intent_radar.permissions import persistence_context
    ctx=persistence_context(c)
    if job_id and not c.execute("UPDATE intelligence_jobs SET updated_at=updated_at WHERE id=? AND organization_id=? AND status='RUNNING' AND lease_owner=? AND lease_until>?",(job_id,ctx.organization_id,lease_owner,now())).rowcount:raise ExecutionInvalidated('Worker lease was replaced before persistence.')
    if discovery['monitor_id'] and not c.execute("UPDATE intent_monitors SET updated_at=updated_at WHERE id=? AND organization_id=? AND status='Active' AND revision=?",(discovery['monitor_id'],ctx.organization_id,discovery['monitor_revision'])).rowcount:raise ExecutionInvalidated('Monitor changed before persistence.')
    for key,value in sorted(discovery.get('source_configs',{}).items()):
        if not c.execute('UPDATE intent_source_configs SET updated_at=updated_at WHERE organization_id=? AND id=? AND configuration_json=?',(ctx.organization_id,key,value)).rowcount:raise ExecutionInvalidated('Approved source configuration changed before persistence.')

async def process(c,key,job_id=None,lease_owner=None):
    ctx=context(c,True);discovery=service.get(c,'discoveries',key)
    query=models.Search.model_validate(discovery['configuration'])
    discovery['source_configs']={r['id']:r['configuration_json'] for r in c.execute('SELECT id,configuration_json FROM intent_source_configs WHERE organization_id=?',(ctx.organization_id,)).fetchall() if r['id'] in list(map(str,query.feed_ids))}
    def permit():
        context(c,True)
        if discovery['monitor_id']:
            monitor=service.get(c,'monitors',discovery['monitor_id'])
            if monitor['status']!='Active' or monitor['revision']!=discovery['monitor_revision']:raise ExecutionInvalidated('Monitor configuration or status changed.')
        if job_id:
            from app.intelligence.jobs import owned,valid_lease
            row=owned(c,job_id)
            if not valid_lease(row,lease_owner):raise ExecutionInvalidated('Worker lease is no longer active.')
        for key,value in discovery['source_configs'].items():
            row=c.execute('SELECT configuration_json FROM intent_source_configs WHERE organization_id=? AND id=?',(ctx.organization_id,key)).fetchone()
            if not row or row[0]!=value:raise ExecutionInvalidated('Approved source configuration changed during collection.')
        return True
    # Adapters use the same transaction fence before writing a response cache.
    # A callback check alone cannot close the revoke/check/write race.
    permit.fence=lambda:fence(c,discovery,job_id,lease_owner)
    permit()
    connectors.validate(c,query)
    found=[];new=0;new_ids=set();reports=[];requests=0;scanned=0;synthetic=False
    for provider in dict.fromkeys(query.sources):
        permit()
        configuration_hash=hashlib.sha256(json.dumps(query.model_dump(),sort_keys=True,default=str).encode()).hexdigest()
        query._collection_cursor={}
        if discovery['monitor_id']:
            cursor=c.execute('SELECT cursor_json FROM intent_collection_cursors WHERE organization_id=? AND monitor_id=? AND provider=? AND configuration_hash=?',(ctx.organization_id,discovery['monitor_id'],provider,configuration_hash)).fetchone()
            if cursor:query._collection_cursor=json.loads(cursor[0])
        provider_start=len(found)
        provider_new_start=new
        provider_new_ids=set(new_ids)
        provider_limit=max(1,(query.result_limit+len(query.sources)-1)//len(query.sources))
        checkpoint=c.execute('SELECT status,result_json FROM intent_source_runs WHERE organization_id=? AND discovery_id=? AND provider=?',(ctx.organization_id,key,provider)).fetchone()
        if checkpoint and checkpoint['status'] in ('COMPLETE','NO_RESULTS'):
            saved=json.loads(checkpoint['result_json'])
            # Only versioned checkpoints with persisted IDs can be resumed.
            # Current approval, membership, monitor revision and lease have
            # already been checked above; stored IDs never grant access.
            if 'signals' in saved:
                new_ids.update(saved.get('new_signal_ids',[]))
                fence(c,discovery,job_id,lease_owner)
                for signal_id in saved['signals']:
                    owned_signal=c.execute('SELECT id FROM intent_signals WHERE organization_id=? AND id=? AND available=1',(ctx.organization_id,signal_id)).fetchone()
                    if owned_signal and signal_id not in found and len(found)<query.result_limit:found.append(signal_id)
                new+=saved.get('new_signals',0)
                requests+=saved.get('requests') or 0;scanned+=saved.get('scanned') or 0
                synthetic|=bool(saved.get('synthetic',False));reports.append(saved)
                c.commit();continue
        try:
            c.commit()
            from app.intent_radar.operations import reserve_source
            reserve_source(provider)
            source=await asyncio.wait_for(connectors.fetch(c,query,provider,permit),timeout=FETCH_TIMEOUT_SECONDS)
            source=models.SourceResult.model_validate(source).model_dump(exclude_none=True)
            permit();fence(c,discovery,job_id,lease_owner)
            requests+=source['requests'];scanned+=source['scanned'];synthetic|=bool(source.get('synthetic',False))
            for raw in source['items']:
                if raw['removed']:
                    removed=c.execute('SELECT id FROM intent_signals WHERE organization_id=? AND source=? AND source_record_id=?',(ctx.organization_id,raw.get('source','Hacker News'),raw['source_record_id'])).fetchone()
                    c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json='{}',revision=revision+1 WHERE organization_id=? AND source=? AND source_record_id=?",(ctx.organization_id,raw.get('source','Hacker News'),raw['source_record_id']))
                    if removed:
                        c.execute('DELETE FROM intent_analyses WHERE organization_id=? AND signal_id=?',(ctx.organization_id,removed['id']))
                        c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id=?',(ctx.organization_id,removed['id']))
                        c.execute("UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND signal_id=?",(ctx.organization_id,removed['id']))
                    continue
                item=classify(raw,query)
                if not item or len(found)>=query.result_limit or len(found)-provider_start>=provider_limit:continue
                item['evidence'].update(test_fixture=bool(source.get('synthetic',False)),provenance=raw.get('provenance',{}),content_fingerprint=raw.get('content_fingerprint'),discussion_id=raw.get('discussion_id'),discovery_id=key,search_configuration=discovery['configuration'])
                # Canonical URL equality merges the same item across approved feeds;
                # similar titles alone never merge distinct conversations.
                old=c.execute('SELECT id,evidence_json FROM intent_signals WHERE organization_id=? AND source=? AND (source_record_id=? OR source_url=?) ORDER BY id LIMIT 1',(ctx.organization_id,item['source'],item['source_record_id'],item['source_url'])).fetchone()
                if old and json.loads(old['evidence_json']).get('removed_by_policy'):continue
                signal=old['id'] if old else str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id+':'+('HN' if provider=='hacker_news' else item['source'])+':'+item['source_record_id']))
                changed=c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,source,source_record_id) DO NOTHING',(signal,ctx.organization_id,item['source'],item['source_record_id'],item['source_url'],item['title'],item['excerpt'],item['observed_at'],item['retrieved_at'],item['category'],item['score'],json.dumps(item['evidence']))).rowcount if not old else 0
                new+=changed
                if changed:new_ids.add(signal)
                if signal not in found:found.append(signal)
                if not changed:
                    c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id=?',(ctx.organization_id,signal))
                    c.execute('UPDATE intent_signals SET title=?,excerpt=?,retrieved_at=?,evidence_json=?,category=?,score=?,available=1 WHERE id=? AND organization_id=?',(item['title'],item['excerpt'],item['retrieved_at'],json.dumps(item['evidence']),item['category'],item['score'],signal,ctx.organization_id))
                if discovery['monitor_id'] and not query.semantic:
                    linked=c.execute('INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,monitor_id,signal_id) DO NOTHING',(ctx.organization_id,discovery['monitor_id'],signal,now())).rowcount
                    prefs=service.preferences(c)
                    if linked and prefs['alerts_enabled']:service.alert(c,'match:'+discovery['monitor_id']+':'+signal,'High-relevance signal to review' if item['score']>=prefs['alert_threshold'] else 'Monitor found a matching discussion',item['title'],discovery['monitor_id'],signal,discovery['created_by'])
            report={'provider':provider,'status':source.get('status') if source.get('errors') else 'COMPLETE' if source['items'] else 'NO_RESULTS','requests':source['requests'],'scanned':source['scanned'],'coverage':source['coverage'],'quota_remaining':source.get('quota_remaining'),'next_offset':source.get('next_offset'),'errors':source.get('errors',[]),'signals':found[provider_start:],'new_signals':new-provider_new_start,'synthetic':bool(source.get('synthetic',False))}
        except ExecutionInvalidated:raise
        except Exception as exc:
            found=found[:provider_start];new=provider_new_start;new_ids=provider_new_ids
            c.rollback();permit();fence(c,discovery,job_id,lease_owner)
            report={'provider':provider,'status':getattr(exc,'code','TIMED_OUT' if isinstance(exc,TimeoutError) else 'UNAVAILABLE'),'retry_at':getattr(exc,'retry_at',None),'requests':None,'request_count_known':False,'coverage':'Source did not complete; coverage and exact request count unavailable.'}
            if len(query.sources)==1:
                c.execute('INSERT INTO intent_source_runs(organization_id,discovery_id,provider,status,result_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,discovery_id,provider) DO UPDATE SET status=excluded.status,result_json=excluded.result_json,updated_at=excluded.updated_at',(ctx.organization_id,key,provider,report['status'],json.dumps(report),now()))
                c.commit();raise
            if service.preferences(c)['alerts_enabled']:service.alert(c,'source-failure:'+key+':'+provider,'Intent source unavailable',provider+': '+report['status'],discovery['monitor_id'],actor=discovery['created_by'])
        report['new_signal_ids']=[signal_id for signal_id in report.get('signals',[]) if signal_id in new_ids]
        if query.semantic:report['candidates_retained']=len(report.get('signals',[]));report['matched']=0
        reports.append(report)
        c.execute('INSERT INTO intent_source_runs(organization_id,discovery_id,provider,status,result_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,discovery_id,provider) DO UPDATE SET status=excluded.status,result_json=excluded.result_json,updated_at=excluded.updated_at',(ctx.organization_id,key,provider,report['status'],json.dumps(report),now()))
        # Progressive results are committed only under the original lease/revision fence.
        if discovery['monitor_id'] and report['status'] in ('COMPLETE','NO_RESULTS') and source.get('cursor') is not None:
            fence(c,discovery,job_id,lease_owner)
            c.execute('INSERT INTO intent_collection_cursors(organization_id,monitor_id,provider,configuration_hash,cursor_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,monitor_id,provider) DO UPDATE SET configuration_hash=excluded.configuration_hash,cursor_json=excluded.cursor_json,updated_at=excluded.updated_at',(ctx.organization_id,discovery['monitor_id'],provider,configuration_hash,json.dumps(source['cursor']),now()))
        c.commit()
    permit();fence(c,discovery,job_id,lease_owner)
    semantic_reports=[]
    if query.semantic:
        from app.intent_radar import intelligence
        retained={signal_id:service.get(c,'signals',signal_id) for signal_id in dict.fromkeys(found)}
        groups=[sorted(report.get('signals',[]),key=lambda signal_id:(-retained[signal_id]['keyword_score'],signal_id)) for report in reports]
        candidates=[];seen_urls=set()
        while any(groups) and len(candidates)<query.semantic_analysis_limit:
            for group in groups:
                if group and len(candidates)<query.semantic_analysis_limit:
                    signal_id=group.pop(0);url=retained[signal_id]['source_url'].split('#',1)[0]
                    if url in seen_urls:continue
                    seen_urls.add(url);candidates.append(signal_id)
        for signal_id in candidates:
            permit();c.commit()
            analyzed=await intelligence.analyze(c,signal_id,models.AnalysisRequest(icp_id=query.icp_id,monitor_id=discovery['monitor_id'],summary_language=query.summary_language),candidate_monitor=True,persistence_fence=lambda connection:fence(connection,discovery,job_id,lease_owner))
            permit();fence(c,discovery,job_id,lease_owner)
            interpretation=analyzed['interpretation']
            supported=bool(interpretation and any(claim['kind'] in ('semantic','icp') for claim in interpretation['claims']))
            accepted=supported and not analyzed['excluded'] and analyzed['scoring']['overall']>=query.min_relevance
            if query.language!='Any / unverified':accepted=accepted and bool(analyzed['interpretation'] and analyzed['interpretation']['detected_language']==query.language)
            semantic_reports.append({'signal_id':signal_id,'mode':analyzed['mode'],'score':analyzed['scoring']['overall'],'accepted':accepted,'reason':analyzed['fallback_reason'] or (None if supported else 'No cited semantic alignment was returned.'),'excluded':analyzed['excluded'],'keyword_score':service.get(c,'signals',signal_id)['keyword_score']})
            c.commit()
        accepted={r['signal_id'] for r in semantic_reports if r['accepted']}
        # Unevaluated/failed candidates cannot be advertised as semantic matches.
        found=[s for s in found if s in accepted]
        scored={r['signal_id']:r['score'] for r in semantic_reports}
        found.sort(key=lambda s:(-scored.get(s,service.get(c,'signals',s)['score']),s))
        if discovery['monitor_id']:
            for signal_id in found:
                linked=c.execute('INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,monitor_id,signal_id) DO NOTHING',(ctx.organization_id,discovery['monitor_id'],signal_id,now())).rowcount
                prefs=service.preferences(c)
                if linked and prefs['alerts_enabled']:
                    signal=service.get(c,'signals',signal_id)
                    service.alert(c,'match:'+discovery['monitor_id']+':'+signal_id,'High-relevance signal to review' if scored[signal_id]>=prefs['alert_threshold'] else 'Monitor found a matching discussion',signal['title'],discovery['monitor_id'],signal_id,discovery['created_by'])
    # Source collection is permitted to members; retention scrubbing is an
    # administrator operation handled independently by the scheduler.
    from app.api.organization import membership_role
    if membership_role(c,ctx.actor,ctx.organization_id) in ('OWNER','ADMIN'):service.expire_content(c)
    for report in reports:
        report['semantic_evaluations']=[r for r in semantic_reports if r['signal_id'] in report.get('signals',[])]
        if query.semantic:
            report['candidates_retained']=len(report.get('signals',[]))
            report['matched']=sum(signal_id in accepted for signal_id in report.get('signals',[]))
            report['new_signals']=sum(signal_id in accepted and signal_id in new_ids for signal_id in report.get('signals',[]))
        report['new_signal_ids']=[signal_id for signal_id in report.get('signals',[]) if signal_id in new_ids]
        fence(c,discovery,job_id,lease_owner)
        c.execute('UPDATE intent_source_runs SET result_json=?,updated_at=? WHERE organization_id=? AND discovery_id=? AND provider=?',(json.dumps(report),now(),ctx.organization_id,key,report['provider']))
    if discovery['monitor_id']:c.execute('UPDATE intent_monitors SET last_checked=? WHERE id=? AND organization_id=?',(now(),discovery['monitor_id'],ctx.organization_id))
    source_name=next(s['name'] for s in connectors.catalog(c) if s['id']==query.sources[0]) if len(query.sources)==1 else 'Multiple sources'
    return {'status':'COMPLETE','coverage_status':'PARTIAL' if any(r['status'] not in ('COMPLETE','NO_RESULTS') for r in reports) else 'COMPLETE','signals':found,'new_signals':len(new_ids.intersection(found)) if query.semantic else new,'new_candidate_signals':new,'matched':len(found),'source':source_name,'sources':reports,'requests':requests,'scanned':scanned,'coverage':'; '.join(r['coverage'] for r in reports),'next_offset':reports[0].get('next_offset'),'classification':'DETERMINISTIC_V3','synthetic':synthetic}

def owned_job(c,key):
    context(c)
    from app.intelligence import jobs
    row=jobs.owned(c,key)
    if row['kind']!='INTENT_DISCOVER':raise HTTPException(404,'Intent Radar job not found.')
    result=jobs.detail(c,key)
    org=context(c).organization_id
    item_row=c.execute('SELECT i.resource_id FROM intelligence_job_items i JOIN intelligence_jobs j ON j.id=i.job_id WHERE j.id=? AND j.organization_id=? ORDER BY i.id LIMIT 1',(key,org)).fetchone()
    if item_row:result['discovery_id']=item_row['resource_id']
    result['sources']=[json.loads(r[0]) for r in c.execute('SELECT r.result_json FROM intent_source_runs r JOIN intelligence_job_items i ON i.resource_id=r.discovery_id JOIN intelligence_jobs j ON j.id=i.job_id AND j.organization_id=r.organization_id WHERE j.id=? AND j.organization_id=? ORDER BY r.provider',(key,org)).fetchall()]
    return result

def usage(c):
    org=context(c).organization_id;settings=get_settings();day=datetime.now(timezone.utc).date().isoformat()
    ai_usage=c.execute('SELECT calls,reserved_tokens FROM intent_analysis_usage WHERE organization_id=? AND day=?',(org,day)).fetchone()
    return {'searches_today':c.execute('SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=? AND created_at>=?',(org,day)).fetchone()[0],
            'daily_search_limit':settings.intent_radar_daily_searches,'monitor_limit':settings.intent_radar_monitor_limit,
            'requests_per_check':33,'automatic_schedules_enabled':settings.intent_radar_schedules_enabled,'minimum_schedule_hours':settings.intent_radar_min_schedule_hours,'paid_subscription_claimed':False,'source_cost':'Approved public APIs/feeds; no paid data provider',
            'source_requests_known':sum(json.loads(r[0]).get('requests') or 0 for r in c.execute('SELECT result_json FROM intent_source_runs WHERE organization_id=? AND updated_at>=?',(org,day)).fetchall()),'source_request_accounting':'Completed checks only; failed transport request counts may be unknown','ai_calls_reserved':ai_usage['calls'] if ai_usage else 0,'ai_tokens_reserved':ai_usage['reserved_tokens'] if ai_usage else 0,'ai_daily_token_limit':settings.intent_radar_ai_daily_tokens,'actual_ai_token_usage':'Provider-reported usage available separately at /usage/provider; reservations are not billed tokens'}
