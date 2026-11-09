"""Owner-authorized verified rollback checkpoint; snapshot alone never deletes data."""
import os,sys,json,zipfile,hashlib,uuid,argparse
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import get_connection
from psycopg import sql

def ident(c,pattern,*names):return sql.SQL(pattern).format(*(sql.Identifier(x) for x in names)).as_string(c.raw)
def paused(c):
    controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone()
    assert controls['scan_paused'] and controls['email_paused'],'Pause controls first'
    assert not c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL").fetchone()[0],'Active scan worker'
    assert not c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0],'Active report worker'
    assert not c.execute("SELECT COUNT(*) FROM email_messages WHERE status='SENDING'").fetchone()[0],'Unresolved SMTP reservation'

def snapshot(reason,artifacts=False):
    folder=Path('data/backups');folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');archive=folder/(reason+'-'+stamp+'.zip');state=folder/(reason+'-'+stamp+'.json')
    c=get_connection(session_bound=True);manifest={'created_at':datetime.now(timezone.utc).isoformat(),'reason':reason,'tables':{},'objects':{},'missing_objects':[],'format':'PostgreSQL binary COPY, ordered column metadata, sequences and schema implementation'}
    storage=None;keys=set()
    try:
        paused(c);c.commit();c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        manifest['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
        columns={}
        for r in c.execute("SELECT table_name,column_name,data_type,udt_name,column_default,is_nullable FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position").fetchall():columns.setdefault(r['table_name'],[]).append(dict(r))
        manifest['sequences']=[dict(r) for r in c.execute("SELECT schemaname,sequencename,last_value FROM pg_sequences WHERE schemaname='public'").fetchall()]
        if artifacts:
            from app.storage import R2ArtifactStorage,validate_key
            storage=R2ArtifactStorage()
            for prefix in ('campaigns/','prospects/','audits/'):
                for page in storage.client.get_paginator('list_objects_v2').paginate(Bucket=storage.bucket,Prefix=prefix):keys.update(validate_key(r['Key']) for r in page.get('Contents',[]))
            keys.update(validate_key(r[0]) for r in c.execute('SELECT object_key FROM artifact_objects UNION SELECT object_key FROM client_reports WHERE object_key IS NOT NULL UNION SELECT object_key FROM website_captures WHERE object_key IS NOT NULL').fetchall())
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
            os.chmod(archive,0o600)
            for table in tables:
                count=c.execute(ident(c,'SELECT COUNT(*) FROM {}',table)).fetchone()[0];digest=hashlib.sha256();size=0
                with z.open('db/'+table+'.copybin','w',force_zip64=True) as output:
                    with c.raw.cursor().copy(sql.SQL('COPY {} TO STDOUT (FORMAT BINARY)').format(sql.Identifier('public',table))) as copy:
                        for block in copy:output.write(block);digest.update(block);size+=len(block)
                manifest['tables'][table]={'count':count,'columns':columns[table],'bytes':size,'sha256':digest.hexdigest()}
            if artifacts:
                from botocore.exceptions import ClientError
                for key in sorted(keys):
                    try:body=storage.get(key)
                    except ClientError as exc:
                        if exc.response.get('Error',{}).get('Code') in ('NoSuchKey','404','NotFound'):manifest['missing_objects'].append(key);continue
                        raise
                    digest=hashlib.sha256();size=0
                    with body,z.open('objects/'+key,'w',force_zip64=True) as output:
                        while block:=body.read(1024*1024):output.write(block);digest.update(block);size+=len(block)
                    manifest['objects'][key]={'bytes':size,'sha256':digest.hexdigest()}
            for path in Path('app/database').glob('*.py'):z.write(path,'schema-source/'+path.name)
            z.writestr('manifest.json',json.dumps(manifest,indent=2,default=str))
        c.commit()
        print(json.dumps({'checkpoint_created':str(archive),'tables':len(tables),'objects':len(manifest['objects']),'restore_verification':'running'}),flush=True)
        schema='foundation_verify_'+uuid.uuid4().hex
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for table,meta in manifest['tables'].items():assert hashlib.sha256(z.read('db/'+table+'.copybin')).hexdigest()==meta['sha256']
            for key,meta in manifest['objects'].items():assert hashlib.sha256(z.read('objects/'+key)).hexdigest()==meta['sha256']
            c.execute(ident(c,'CREATE SCHEMA {}',schema))
            for table,meta in manifest['tables'].items():
                query=sql.SQL('CREATE TABLE {} (LIKE {} INCLUDING ALL)').format(sql.Identifier(schema,table),sql.Identifier('public',table));c.execute(query.as_string(c.raw))
                with c.raw.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier(schema,table))) as copy:
                    with z.open('db/'+table+'.copybin') as source:
                        while block:=source.read(1024*1024):copy.write(block)
                query=sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(schema,table));assert c.execute(query.as_string(c.raw)).fetchone()[0]==meta['count']
            c.execute(ident(c,'DROP SCHEMA {} CASCADE',schema));c.commit()
        record={'backup':str(archive.resolve()),'backup_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'schema':manifest['schema'],'backup_verified':True,'restore_test_passed':True,'artifacts_included':artifacts,'before':{t:m['count'] for t,m in manifest['tables'].items()},'cleared':False}
        state.write_text(json.dumps(record,indent=2));os.chmod(state,0o600)
        print(json.dumps({'verified':True,'state':str(state),'schema':manifest['schema'],'tables':len(tables),'objects':len(manifest['objects'])}),flush=True)
        return state
    finally:c.close()

def migrate(state):
    record=json.loads(Path(state).read_text());assert record['backup_verified'] and record['restore_test_passed'] and record['schema']==11
    assert hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest()==record['backup_sha256']
    from app.database.migrations import run_migrations
    c=get_connection(session_bound=True)
    try:
        paused(c);version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0];assert version in (11,12)
        applied=run_migrations(c) if version==11 else 0
        assert applied==(1 if version==11 else 0)
        assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==12
        volatile={'internal_request_nonces','email_sync_state','email_sync_lock','email_accounts','schema_migrations'}
        for table,count in record['before'].items():
            if table not in volatile:assert c.execute(ident(c,'SELECT COUNT(*) FROM {}',table)).fetchone()[0]==count,table
        paused(c)
        c.execute("INSERT INTO recovery_checkpoints(id,created_at,schema_version,reason,target_version,status,artifact_path,manifest_json) VALUES(?,?,11,'FOUNDATION_UPGRADE',12,'RESTORE_VERIFIED',?,?)",(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),record['backup'],json.dumps({'sha256':record['backup_sha256']})));c.commit()
        record.update(migrated=True,after_schema=12,preserved=True);Path(state).write_text(json.dumps(record,indent=2));print(json.dumps({'schema':12,'applied':applied,'preserved':True}))
    finally:c.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['snapshot','migrate']);p.add_argument('--reason',default='foundation-schema11');p.add_argument('--artifacts',action='store_true');p.add_argument('--state');a=p.parse_args()
    if a.action=='snapshot':snapshot(a.reason,a.artifacts)
    else:migrate(a.state)
