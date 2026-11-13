"""Read-only production snapshot, restore and upgrade in a private local PG18 DB.

Never restores to production. Credentials stay in process memory/child environment.
"""
import hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,unquote
import psycopg
from psycopg import sql
from dotenv import dotenv_values
from app.database.postgres import PostgresConnection,session_url
from app.database.migrations import run_migrations,verify_schema

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'data/artifacts/runtime/postgres18-install/bin'
LOCAL='postgresql://planebyte@/postgres?host=/private/tmp/planebyte-beta-pg18&port=15433'

def fingerprint(c,tables=None):
    tables=tables or [r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    result={}
    for table in tables:
        rows=c.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t').format(sql.Identifier(table))).fetchall()
        digests=sorted(hashlib.sha256(row[0].encode()).hexdigest() for row in rows)
        result[table]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(digests).encode()).hexdigest()}
    return result

def run(name,args,env,folder):
    with (folder/(name+'.log')).open('w') as log:
        p=subprocess.run([str(BIN/name),*args],env=env,stdout=log,stderr=log,timeout=900)
    if p.returncode:raise RuntimeError(name+' failed; inspect restricted backup log locally.')

def main():
    os.umask(0o077)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=ROOT/'data/backups'/('beta-recovery-'+stamp);folder.mkdir(parents=True,mode=0o700)
    conf=dotenv_values(ROOT/'.env',interpolate=False);source=session_url(conf['DATABASE_URL'])
    parsed=urlsplit(source)
    if not (parsed.hostname or '').endswith('.neon.tech'):raise RuntimeError('Expected existing production Neon source.')
    env={**os.environ,'PGHOST':parsed.hostname,'PGPORT':str(parsed.port or 5432),'PGUSER':unquote(parsed.username or ''),'PGPASSWORD':unquote(parsed.password or ''),'PGDATABASE':unquote(parsed.path.lstrip('/')),'PGSSLMODE':'require','PGCONNECT_TIMEOUT':'15'}
    dump=folder/'production.dump'
    with psycopg.connect(source,autocommit=True,connect_timeout=15) as c:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        c.execute('SET LOCAL statement_timeout=30000')
        snapshot=c.execute('SELECT pg_export_snapshot()').fetchone()[0]
        before=fingerprint(c)
        version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        run('pg_dump',['--format=custom','--compress=none','--snapshot='+snapshot,'--file='+str(dump)],env,folder)
        c.execute('ROLLBACK')
    db='beta_restore_'+stamp.lower()
    with psycopg.connect(LOCAL,autocommit=True) as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(db)))
    target=LOCAL.replace('/postgres?','/'+db+'?')
    # Discard inherited remote DB variables; the restore can only target our socket.
    local_env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
    run('pg_restore',['--no-owner','--no-privileges','--exit-on-error','--dbname='+target,str(dump)],local_env,folder)
    with psycopg.connect(target) as c:restored=fingerprint(c)
    if before!=restored:raise RuntimeError('Restored source fingerprints differ.')
    adapter=PostgresConnection(target)
    try:
        applied=run_migrations(adapter);verify_schema(adapter)
        if run_migrations(adapter)!=0:raise RuntimeError('Migrations are not idempotent.')
        owner=[dict(r) for r in adapter.execute("SELECT o.id,o.name,m.user_id,m.role FROM organizations o JOIN organization_memberships m ON m.organization_id=o.id WHERE o.slug='planebyte' AND m.status='ACTIVE'").fetchall()]
        adapter.commit()
    finally:adapter.close()
    with psycopg.connect(target) as c:after=fingerprint(c,list(before))
    changed={k:{'before':before[k],'after':after[k]} for k in before if before[k]!=after[k]}
    lost=[k for k in before if after[k]['count']<before[k]['count']]
    if lost:raise RuntimeError('Migration lost rows in '+','.join(lost))
    result={'backup':str(dump),'backup_sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),'backup_bytes':dump.stat().st_size,'source_schema':version,'restored_exactly':True,'migrations_applied':applied,'target_schema':version+applied,'second_migration_run':0,'row_loss':lost,'changed_tables':changed,'verified_memberships':owner,'local_restore_database':db}
    (folder/'recovery-result.json').write_text(json.dumps(result,indent=2))
    (folder/'source-fingerprints.json').write_text(json.dumps(before,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as error:
        # No connection strings/provider exceptions in terminal output.
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__}));raise SystemExit(1)
