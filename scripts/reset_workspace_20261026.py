"""One explicitly user-authorized production workspace reset, with idle checks."""
import os,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.storage import R2ArtifactStorage,validate_key
from app.database.prospects import now

record=Path('docs/workspace-reset-20261026.json')
if record.exists() and json.loads(record.read_text(encoding='utf-8')).get('completed'):
    raise SystemExit('This reset already completed. Refusing to delete fresh scan data.')
tables=['deletion_targets','deletion_batches','social_profile_sources','social_profiles','business_intelligence','website_captures','client_reports','artifact_objects','prospect_notes','prospect_observations','business_identities','opportunity_scores','lead_scores','lighthouse_results','findings','contacts','website_profiles','businesses','prospects','pipeline_run_events','pipeline_runs','scan_campaigns']
with db_session() as c:
    c.execute('SELECT pg_advisory_xact_lock(691944307)')
    c.execute('SELECT pg_advisory_xact_lock(691944303)')
    c.execute('SELECT pg_advisory_xact_lock(691944302)')
    if c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL").fetchone()[0]:raise RuntimeError('Active scan found; reset stopped.')
    if c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]:raise RuntimeError('Active report found; reset stopped.')
    counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
    storage=R2ArtifactStorage();keys=set()
    for prefix in ('campaigns/','prospects/','audits/'):
        for page in storage.client.get_paginator('list_objects_v2').paginate(Bucket=storage.bucket,Prefix=prefix):
            keys.update(validate_key(o['Key']) for o in page.get('Contents',[]))
    keys.update(r[0] for r in c.execute('SELECT object_key FROM artifact_objects UNION SELECT object_key FROM client_reports WHERE object_key IS NOT NULL').fetchall())
    manifest=Path('tmp/workspace-reset-20261026-objects.json');manifest.parent.mkdir(exist_ok=True);manifest.write_text(json.dumps(sorted(keys)),encoding='utf-8')
    storage.delete_many(sorted(keys))
    remaining=0
    for prefix in ('campaigns/','prospects/','audits/'):
        remaining+=storage.client.list_objects_v2(Bucket=storage.bucket,Prefix=prefix,MaxKeys=1).get('KeyCount',0)
    if remaining:raise RuntimeError('Private object cleanup incomplete; database reset stopped.')
    c.execute('TRUNCATE TABLE '+','.join(tables)+' RESTART IDENTITY')
    after={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
    assert not any(after.values())
    c.commit()
    result={'completed':True,'completed_at':now(),'before':counts,'after':after,'private_objects_deleted':len(keys),'preserved':['schema_migrations','users','shared_settings','internal_request_nonces'],'authorization':'User: clean the entire database and start a fresh scan.'}
    record.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'completed':True,'old_observations_removed':counts['businesses'],'old_leads_removed':counts['prospects'],'old_scans_removed':counts['pipeline_runs'],'old_reports_removed':counts['client_reports'],'private_objects_deleted':len(keys),'all_workspace_tables_empty':not any(after.values())}))
