"""Read-only release evidence and explicitly disposable deletion QA fixtures."""
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database.connection import db_session
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.storage import artifact_storage,publish_artifact
os.environ['DATABASE_BACKEND']='postgres'
os.environ['STORAGE_BACKEND']='r2'
action=sys.argv[1] if len(sys.argv)>1 else 'status'
if action=='seed-delete-qa':
    record=Path('tmp/phase36-delete-qa.json')
    if record.exists():raise SystemExit('Disposable QA fixtures already recorded; reuse that record.')
    state={'targets':[],'business_ids':[],'run_ids':[],'object_keys':[],'campaign_ids':[],'prospect_ids':[]}
    with db_session() as c:
        cid=str(uuid.uuid4());state['campaign_ids'].append(cid)
        c.execute("INSERT INTO scan_campaigns(id,created_by,status,configuration_json,target_total,created_at) VALUES(?,?,'COMPLETED',?,5,?)",(cid,'planebyte@gmail.com',json.dumps({'cities':['Phase36 deletion QA'],'verticals':['dentists']}),now()))
        for i in range(4):
            run=PipelineRun(market='Phase36 deletion QA',vertical='dentists',target=5,status='COMPLETED');PipelineRunRepository(c).create(run);state['run_ids'].append(run.id)
            if i==0:c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
            group='shared' if i<2 else 'lead';host=f'phase36-qa-{cid}-{group}.invalid'
            b=Business(name='Phase36 deletion QA '+group,normalized_name='phase36 deletion qa '+group,vertical='dentists',city='QA',country='QA',address='1 QA Street',domain=host,website='https://'+host,run_id=run.id)
            BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b,cid if i==0 else None);state['business_ids'].append(b.id);state['prospect_ids'].append(pid)
            with tempfile.TemporaryDirectory() as folder:
                file=Path(folder)/'qa.csv';file.write_text('QA only',encoding='utf-8');key=f'campaigns/{cid}/qa-{run.id}.csv';publish_artifact(c,key,file,run_id=run.id,kind='csv');state['object_keys'].append(key)
        state['targets']=[{'kind':'campaign','id':cid},{'kind':'scan','id':state['run_ids'][1]},{'kind':'lead','id':state['business_ids'][2]},{'kind':'scan','id':state['run_ids'][2]},{'kind':'scan','id':state['run_ids'][3]}]
    record.parent.mkdir(exist_ok=True);record.write_text(json.dumps(state,indent=2),encoding='utf-8');print('Created four disposable runs, two QA lead identities and private QA exports.')
elif action=='verify-delete-qa':
    state=json.loads(Path('tmp/phase36-delete-qa.json').read_text(encoding='utf-8'));checks={}
    with db_session() as c:
        for table,ids in [('businesses',state['business_ids']),('pipeline_runs',state['run_ids']),('prospects',state['prospect_ids']),('scan_campaigns',state['campaign_ids'])]:checks[table+'_removed']=c.execute('SELECT COUNT(*) FROM '+table+' WHERE id IN ('+','.join('?' for _ in ids)+')',ids).fetchone()[0]==0
    removed=0
    for key in state['object_keys']:
        try:
            with artifact_storage().get(key) as body:body.read(1)
        except Exception as e:
            if getattr(e,'response',{}).get('Error',{}).get('Code') in ('NoSuchKey','404'):removed+=1
            else:raise
    checks['private_objects_removed']=removed==len(state['object_keys']);Path('docs/phase36-deletion-qa.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps(checks));assert all(checks.values())
else:
    result={}
    with db_session() as c:
        result['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        result['counts']={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('scan_campaigns','pipeline_runs','businesses','prospects','client_reports')}
        if result['schema']>=6:
            result['pending_deletions']=c.execute('SELECT COUNT(*) FROM deletion_batches').fetchone()[0]
            record=Path('docs/phase36-production.json')
            if record.exists():
                campaign=json.loads(record.read_text(encoding='utf-8')).get('campaign')
                if campaign:
                    result['campaign_events']=[dict(r) for r in c.execute("SELECT e.timestamp,e.event_type FROM pipeline_run_events e JOIN pipeline_runs r ON r.id=e.run_id WHERE r.campaign_id=? AND e.event_type IN ('AUDIT_COMPLETE','SOCIAL_COMPLETE','RUN_COMPLETED') ORDER BY e.id",(campaign['id'],)).fetchall()]
                    rows=c.execute('SELECT i.*,b.name,b.website,b.processing_status,w.reachable FROM business_intelligence i JOIN businesses b ON b.id=i.business_id JOIN pipeline_runs r ON r.id=b.run_id LEFT JOIN website_profiles w ON w.business_id=b.id WHERE r.campaign_id=?',(campaign['id'],)).fetchall()
                    result['campaign_intelligence']=[dict(r) for r in rows]
                    result['captures']=[dict(r) for r in c.execute('SELECT w.* FROM website_captures w JOIN businesses b ON b.id=w.business_id JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=?',(campaign['id'],)).fetchall()]
                    result['profiles']=[dict(r) for r in c.execute('SELECT DISTINCT s.* FROM social_profiles s JOIN social_profile_sources x ON x.profile_id=s.id JOIN businesses b ON b.id=x.business_id JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=?',(campaign['id'],)).fetchall()]
            targeted=Path('docs/phase36-targeted-reaudit.json')
            if targeted.exists():
                rid=json.loads(targeted.read_text(encoding='utf-8'))['run_id']
                run=c.execute('SELECT id,status,raw_found,qualified,exported,started_at,finished_at FROM pipeline_runs WHERE id=?',(rid,)).fetchone()
                result['targeted_reaudit']={'run':dict(run),'intelligence':[dict(r) for r in c.execute('SELECT i.*,b.name,b.website,b.processing_status,w.reachable FROM business_intelligence i JOIN businesses b ON b.id=i.business_id LEFT JOIN website_profiles w ON w.business_id=b.id WHERE b.run_id=?',(rid,)).fetchall()],'captures':[dict(r) for r in c.execute('SELECT w.* FROM website_captures w JOIN businesses b ON b.id=w.business_id WHERE b.run_id=?',(rid,)).fetchall()]}
    Path('docs/phase36-'+action+'.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');print(json.dumps({'schema':result['schema'],'counts':result['counts'],'assessed':len(result.get('campaign_intelligence',[])),'captures':len(result.get('captures',[]))}))
