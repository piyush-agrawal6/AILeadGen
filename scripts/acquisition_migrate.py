"""Online schema-13 checkpoint/migration. Never pauses or rewrites active workflows."""
import os,sys,json,zipfile,hashlib,uuid,argparse
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import get_connection
from app.database.acquisition_schema import ACQUISITION_SQL
from psycopg import sql

def snapshot():
    folder=Path('data/backups');folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');archive=folder/('acquisition-online-schema12-'+stamp+'.zip');state=folder/('acquisition-online-schema12-'+stamp+'.json')
    manifest={'schema':12,'created_at':datetime.now(timezone.utc).isoformat(),'tables':{},'format':'MVCC consistent PostgreSQL binary COPY; no operational pauses','source_schema_sha256':hashlib.sha256(ACQUISITION_SQL.encode()).hexdigest()};c=get_connection(session_bound=True)
    try:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==12
        manifest['active_scans']=[dict(r) for r in c.execute("SELECT id,status FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED')").fetchall()]
        manifest['active_email_runs']=[dict(r) for r in c.execute("SELECT id,status FROM workflow_runs WHERE kind='OUTREACH' AND status IN ('RUNNING','PREPARING')").fetchall()]
        manifest['controls']=dict(c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone())
        tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
            os.chmod(archive,0o600)
            for table in tables:
                count=c.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(table)).as_string(c.raw)).fetchone()[0];digest=hashlib.sha256()
                columns=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position",(table,)).fetchall()]
                with z.open('db/'+table+'.copybin','w',force_zip64=True) as out:
                    with c.raw.cursor().copy(sql.SQL('COPY {} TO STDOUT (FORMAT BINARY)').format(sql.Identifier(table))) as copy:
                        for block in copy:out.write(block);digest.update(block)
                manifest['tables'][table]={'count':count,'columns':columns,'sha256':digest.hexdigest()}
            manifest['sequences']=[dict(r) for r in c.execute("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public'").fetchall()]
            for path in Path('app/database').glob('*.py'):z.write(path,'schema-source/'+path.name)
            z.writestr('manifest.json',json.dumps(manifest,indent=2,default=str))
        c.commit();print(json.dumps({'snapshot':str(archive),'active_scans_preserved':manifest['active_scans'],'restore_check':'running'}),flush=True)
        schema='acquisition_backup_'+uuid.uuid4().hex
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)).as_string(c.raw))
            for table,meta in manifest['tables'].items():
                assert hashlib.sha256(z.read('db/'+table+'.copybin')).hexdigest()==meta['sha256']
                c.execute(sql.SQL('CREATE TABLE {} (LIKE {} INCLUDING ALL)').format(sql.Identifier(schema,table),sql.Identifier('public',table)).as_string(c.raw))
                with c.raw.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier(schema,table))) as copy:
                    with z.open('db/'+table+'.copybin') as source:
                        while block:=source.read(1024*1024):copy.write(block)
                assert c.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(schema,table)).as_string(c.raw)).fetchone()[0]==meta['count']
            c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)).as_string(c.raw));c.commit()
        record={'backup':str(archive.resolve()),'backup_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restore_verified':True,'before_schema':12,'applied':False,'operational_pauses_changed':False,'active_scans_before':manifest['active_scans'],'controls_before':manifest['controls']};state.write_text(json.dumps(record,indent=2));os.chmod(state,0o600);print(json.dumps({'verified':True,'state':str(state)}),flush=True)
    finally:c.close()

def migrate(path):
    p=Path(path);record=json.loads(p.read_text());assert record['restore_verified'];assert hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest()==record['backup_sha256']
    c=get_connection(session_bound=True)
    try:
        current=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0];c.commit()
        if current==13:print(json.dumps({'schema':13,'already_applied':True}));return
        assert current==12
        c.execute("SET LOCAL lock_timeout='750ms'; SET LOCAL statement_timeout='5s'")
        c.execute('SELECT pg_advisory_xact_lock(691944301)')
        assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==12
        # One server-side DDL round trip and immediate commit: avoid holding campaign
        # metadata locks across dozens of network round trips. Timeout rather than
        # waiting behind active transactions or stopping current workers.
        c.raw.execute(ACQUISITION_SQL+"\nINSERT INTO schema_migrations(version) VALUES(13);")
        c.commit()
        controls=dict(c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone());assert controls==record['controls_before']
        assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==13
        record.update(applied=True,after_schema=13,controls_after=controls,existing_worker_replaced=False,operational_data_reset=False)
        c.execute("INSERT INTO recovery_checkpoints(id,created_at,schema_version,reason,target_version,status,artifact_path,manifest_json) VALUES(?,?,12,'ACQUISITION_PHASE1_ADDITIVE',13,'RESTORE_VERIFIED',?,?)",(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),record['backup'],json.dumps({'sha256':record['backup_sha256']})));c.commit();p.write_text(json.dumps(record,indent=2));print(json.dumps({'schema':13,'applied':1,'controls_preserved':True,'no_operational_reset':True}))
    except Exception:
        c.rollback();raise
    finally:c.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['snapshot','migrate']);parser.add_argument('--state');args=parser.parse_args();snapshot() if args.action=='snapshot' else migrate(args.state)
