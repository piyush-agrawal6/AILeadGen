"""Explicit permanent deletion with previews, worker locks and retryable storage cleanup."""
import hashlib
import json
import uuid
import os
import sys
from pathlib import Path
from fastapi import HTTPException
from app.database.prospects import now
from app.storage import artifact_storage


def inside(column,values):
    return (column+' IN ('+','.join('?' for _ in values)+')',list(values)) if values else ('1=0',[])


def scope(conn,kind,identifier):
    from app.reports.service import expire_reports
    expire_reports(conn)
    conn.execute("UPDATE pipeline_runs SET lease_owner=NULL,lease_expires_at=NULL WHERE status='CANCELLED' AND lease_expires_at<?",(now(),))
    if kind=='campaign':
        row=conn.execute('SELECT configuration_json FROM scan_campaigns WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'Campaign not found.')
        config=json.loads(row[0]);name=', '.join(config.get('cities',[]))+' / '+', '.join(config.get('verticals',[]))
        runs=[r[0] for r in conn.execute('SELECT id FROM pipeline_runs WHERE campaign_id=?',(identifier,)).fetchall()]
        clause,args=inside('run_id',runs);businesses=conn.execute('SELECT id,prospect_id FROM businesses WHERE '+clause,args).fetchall()
    elif kind=='scan':
        if not identifier.isdigit():raise HTTPException(404,'Scan not found.')
        row=conn.execute('SELECT market,vertical FROM pipeline_runs WHERE id=?',(int(identifier),)).fetchone()
        if not row:raise HTTPException(404,'Scan not found.')
        runs=[int(identifier)];name=row[0]+' / '+row[1];businesses=conn.execute('SELECT id,prospect_id FROM businesses WHERE run_id=?',(runs[0],)).fetchall()
    elif kind=='lead':
        if not identifier.isdigit():raise HTTPException(404,'Lead not found.')
        row=conn.execute('SELECT prospect_id,name FROM businesses WHERE id=?',(int(identifier),)).fetchone()
        if not row:raise HTTPException(404,'Lead not found.')
        name=row['name'];businesses=conn.execute('SELECT id,prospect_id FROM businesses WHERE prospect_id=?',(row['prospect_id'],)).fetchall() if row['prospect_id'] else [conn.execute('SELECT id,prospect_id FROM businesses WHERE id=?',(int(identifier),)).fetchone()]
        clause,args=inside('id',[r['id'] for r in businesses]);runs=[r[0] for r in conn.execute('SELECT DISTINCT run_id FROM businesses WHERE '+clause+' AND run_id IS NOT NULL',args).fetchall()]
    else:raise HTTPException(404,'Deletion type not found.')
    bids=sorted(r['id'] for r in businesses);pids=sorted({r['prospect_id'] for r in businesses if r['prospect_id']});orphan=[]
    for pid in pids:
        clause,args=inside('id',bids)
        if not conn.execute('SELECT COUNT(*) FROM businesses WHERE prospect_id=? AND NOT ('+clause+')',[pid]+args).fetchone()[0]:orphan.append(pid)
    bc,ba=inside('business_id',bids);pc,pa=inside('prospect_id',orphan)
    reports=[dict(r) for r in conn.execute('SELECT id,object_key,status,version FROM client_reports WHERE '+bc+' OR '+pc,ba+pa).fetchall()]
    rc,ra=inside('run_id',runs)
    artifacts=conn.execute('SELECT object_key FROM artifact_objects WHERE '+bc+' OR ('+rc+(" AND business_id IS NULL AND kind IN ('csv','xlsx')" if kind=='lead' else '')+')',ba+ra).fetchall()
    keys=sorted({r[0] for r in artifacts}|{r['object_key'] for r in reports if r['object_key']})
    run_clause,run_args=inside('id',runs)
    active_ids={r[0] for r in conn.execute("SELECT id FROM pipeline_runs WHERE (status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL) AND "+run_clause,run_args).fetchall()}
    module=sys.modules.get('app.api.services.scan_manager');manager=getattr(module,'scan_manager',None)
    tasks=getattr(getattr(manager,'executor',None),'_active_tasks',{})
    active_ids.update(run for run in runs if run in tasks and not tasks[run].done())
    active=len(active_ids)
    generating=sum(r['status'] in ('QUEUED','GENERATING') for r in reports)
    result={'kind':kind,'entity_id':identifier,'name':name,'run_ids':runs,'business_ids':bids,'prospect_ids':pids,'orphan_prospect_ids':orphan,'report_ids':sorted(r['id'] for r in reports),'object_keys':keys,'active_scans':active,'active_run_ids':sorted(active_ids),'pending_reports':generating,'shared_leads_retained':len(pids)-len(orphan)}
    result['token']=hashlib.sha256(json.dumps({k:v for k,v in result.items() if k not in ('active_scans','active_run_ids','pending_reports')},sort_keys=True).encode()).hexdigest()
    return result


def preview(conn,kind,identifier):
    data=scope(conn,kind,identifier)
    return {k:data[k] for k in ('name','token','active_scans','active_run_ids','pending_reports','shared_leads_retained')}|{'observations':len(data['business_ids']),'scans':len(data['run_ids']),'reports':len(data['report_ids']),'files':len(data['object_keys']),'canonical_leads':len(data['orphan_prospect_ids']),'removes_related_exports':kind=='lead'}


def delete(conn,kind,identifier,confirmation,token,actor):
    if confirmation!='DELETE':raise HTTPException(422,'Type DELETE to confirm permanent deletion.')
    postgres=getattr(conn,'backend',None)=='postgres'
    if postgres:conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    else:conn.execute('BEGIN IMMEDIATE')
    data=scope(conn,kind,identifier)
    if data['token']!=token:raise HTTPException(409,'The data changed. Review the updated deletion preview and confirm again.')
    if data['active_scans'] or data['pending_reports']:raise HTTPException(409,'Stop the related scans and wait for workers and reports to finish before deleting.')
    from app.config.settings import get_settings
    cleanup_legacy=get_settings().app_env!='test' or bool(os.environ.get('LEGACY_DATA_ROOT'))
    legacy_root=Path(os.environ.get('LEGACY_DATA_ROOT','.')).resolve()
    if postgres:
        for run in data['run_ids']:
            if not conn.execute('SELECT pg_try_advisory_xact_lock(6919445,?)',(run,)).fetchone()[0]:raise HTTPException(409,'A scan worker is still finishing. Retry shortly.')
        for report in data['report_ids']:
            if not conn.execute('SELECT pg_try_advisory_xact_lock(hashtextextended(?,6919446))',(report,)).fetchone()[0]:raise HTTPException(409,'A report worker is still finishing. Retry shortly.')
        clause,args=inside('id',data['prospect_ids'])
        conn.execute('SELECT id FROM prospects WHERE '+clause+' FOR UPDATE',args)
    # Durable intent is committed before object cleanup. A failed cleanup leaves
    # database records and a retryable batch, rather than orphaned storage keys.
    existing=conn.execute('SELECT id FROM deletion_batches WHERE entity_type=? AND entity_id=?',(kind,identifier)).fetchone();batch=existing[0] if existing else str(uuid.uuid4())
    conn.execute("INSERT INTO deletion_batches(id,entity_type,entity_id,actor,scope_json,status,created_at,updated_at) VALUES(?,?,?,?,?,'PENDING',?,?) ON CONFLICT(entity_type,entity_id) DO UPDATE SET scope_json=excluded.scope_json,status='PENDING',error_message=NULL,updated_at=excluded.updated_at",(batch,kind,identifier,actor,json.dumps(data),now(),now()))
    conn.execute('DELETE FROM deletion_targets WHERE request_id=?',(batch,))
    conn.executemany('INSERT INTO deletion_targets(request_id,business_id) VALUES(?,?)',[(batch,bid) for bid in data['business_ids']]);conn.commit()
    try:
        # Reacquire locks after committing durable intent, and keep them until
        # deletion commits. Requests cannot create a report for a pending target.
        if postgres:
            conn.execute('SELECT pg_advisory_xact_lock(691944307)')
            for run in data['run_ids']:
                if not conn.execute('SELECT pg_try_advisory_xact_lock(6919445,?)',(run,)).fetchone()[0]:raise RuntimeError('A worker restarted; retry after it finishes.')
            for report in data['report_ids']:
                if not conn.execute('SELECT pg_try_advisory_xact_lock(hashtextextended(?,6919446))',(report,)).fetchone()[0]:raise RuntimeError('A report worker restarted; retry after it finishes.')
            clause,args=inside('id',data['prospect_ids'])
            conn.execute('SELECT id FROM prospects WHERE '+clause+' FOR UPDATE',args)
        else:conn.execute('BEGIN IMMEDIATE')
        latest=scope(conn,kind,identifier)
        if latest['token']!=data['token'] or latest['active_scans'] or latest['pending_reports']:raise RuntimeError('Deletion scope changed; review a new preview.')
        artifact_storage().delete_many(data['object_keys'])
        bc,ba=inside('business_id',data['business_ids']);rc,ra=inside('run_id',data['run_ids']);pc,pa=inside('prospect_id',data['orphan_prospect_ids'])
        conn.execute('DELETE FROM client_reports WHERE '+bc+' OR '+pc,ba+pa)
        conn.execute('DELETE FROM artifact_objects WHERE '+bc+' OR ('+rc+(" AND business_id IS NULL AND kind IN ('csv','xlsx')" if kind=='lead' else '')+')',ba+ra)
        candidates=[r[0] for r in conn.execute('SELECT DISTINCT profile_id FROM social_profile_sources WHERE '+bc,ba).fetchall()]
        conn.execute('DELETE FROM social_profile_sources WHERE '+bc,ba)
        sc,sa=inside('id',candidates)
        conn.execute('DELETE FROM social_profiles WHERE '+pc+' OR ('+sc+' AND NOT EXISTS(SELECT 1 FROM social_profile_sources s WHERE s.profile_id=social_profiles.id))',pa+sa)
        for table in ('business_intelligence','website_captures','opportunity_scores','prospect_observations'):conn.execute('DELETE FROM '+table+' WHERE '+bc,ba)
        # Core profile/contact/finding/Lighthouse/lead-score tables cascade from businesses.
        clause,args=inside('id',data['business_ids']);conn.execute('DELETE FROM businesses WHERE '+clause,args)
        for table in ('business_identities','prospect_notes'):conn.execute('DELETE FROM '+table+' WHERE '+pc,pa)
        clause,args=inside('id',data['orphan_prospect_ids']);conn.execute('DELETE FROM prospects WHERE '+clause,args)
        for run in data['run_ids']:
            row=conn.execute('SELECT output_file,campaign_id FROM pipeline_runs WHERE id=?',(run,)).fetchone()
            if cleanup_legacy and row and row['output_file']:
                path=Path(row['output_file']).resolve();root=Path('output').resolve()
                if path.is_relative_to(root):
                    path.unlink(missing_ok=True);path.with_suffix('.csv').unlink(missing_ok=True)
            conn.execute('DELETE FROM pipeline_run_events WHERE run_id=?',(run,))
            if kind=='lead':
                counts=conn.execute("SELECT COUNT(*),SUM(CASE WHEN is_rejected=0 THEN 1 ELSE 0 END),SUM(CASE WHEN processing_status='QUALIFIED' AND is_rejected=0 THEN 1 ELSE 0 END) FROM businesses WHERE run_id=?",(run,)).fetchone()
                conn.execute('UPDATE pipeline_runs SET raw_found=?,filtered=?,qualified=?,exported=0,output_file=NULL WHERE id=?',(counts[0],counts[1] or 0,counts[2] or 0,run))
            else:conn.execute('DELETE FROM pipeline_runs WHERE id=?',(run,))
        if kind=='campaign':conn.execute('DELETE FROM scan_campaigns WHERE id=?',(identifier,))
        # Recompute canonical history for leads retained in other campaigns.
        for pid in set(data['prospect_ids'])-set(data['orphan_prospect_ids']):
            history=conn.execute('SELECT MIN(observed_at),MAX(observed_at),COUNT(*) FROM prospect_observations WHERE prospect_id=?',(pid,)).fetchone()
            first=conn.execute('SELECT r.campaign_id FROM prospect_observations o JOIN pipeline_runs r ON r.id=o.run_id WHERE o.prospect_id=? ORDER BY o.observed_at LIMIT 1',(pid,)).fetchone()
            conn.execute('UPDATE prospects SET first_seen_at=COALESCE(?,first_seen_at),last_seen_at=COALESCE(?,last_seen_at),times_discovered=?,first_campaign_id=? WHERE id=?',(history[0],history[1],history[2],first[0] if first else None,pid))
        for bid in data['business_ids'] if cleanup_legacy else []:
            legacy=(legacy_root/'data/lighthouse'/(str(bid)+'.json')).resolve()
            if legacy.is_relative_to(legacy_root):legacy.unlink(missing_ok=True)
            directory=(legacy_root/'output/reports').resolve()
            if directory.is_dir():
                for path in directory.glob(str(bid)+'_*.html'):
                    if path.resolve().is_relative_to(directory):path.unlink(missing_ok=True)
        conn.execute('DELETE FROM deletion_batches WHERE id=?',(batch,));conn.commit()
        return {'deleted':True,'observations':len(data['business_ids']),'files':len(data['object_keys']),'shared_leads_retained':data['shared_leads_retained']}
    except Exception as exc:
        conn.rollback();conn.execute("UPDATE deletion_batches SET status='FAILED',error_message=?,updated_at=? WHERE id=?",(type(exc).__name__+': '+str(exc)[:500],now(),batch));conn.commit()
        raise HTTPException(503,'Deletion is incomplete. Retry to finish removing the remaining data and files.')
