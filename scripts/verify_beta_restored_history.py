"""Compare original columns before/after the local restored-database upgrade."""
import json,os,subprocess
from pathlib import Path
from collections import Counter
import psycopg
from psycopg import sql
from scripts.rehearse_beta_restore import BIN,LOCAL,ROOT

def canonical(value):
    return json.dumps(value,sort_keys=True,default=str,separators=(',',':'))

def main():
    os.umask(0o077)
    recovery=sorted((ROOT/'data/backups').glob('beta-recovery-*/recovery-result.json'))[-1]
    result=json.loads(recovery.read_text());folder=recovery.parent
    name=result['local_restore_database']+'_baseline'
    with psycopg.connect(LOCAL,autocommit=True) as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    before_url=LOCAL.replace('/postgres?','/'+name+'?');after_url=LOCAL.replace('/postgres?','/'+result['local_restore_database']+'?')
    with (folder/'baseline-restore.log').open('w') as log:
        run=subprocess.run([str(BIN/'pg_restore'),'--no-owner','--no-privileges','--exit-on-error','--dbname='+before_url,result['backup']],stdout=log,stderr=log,timeout=180)
    if run.returncode:raise RuntimeError('Local baseline restore failed.')
    differences={};checked=[]
    with psycopg.connect(before_url) as old,psycopg.connect(after_url) as new:
        org=new.execute("SELECT id FROM organizations WHERE slug='planebyte'").fetchone()[0]
        for (table,) in old.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'schema_migrations' ORDER BY tablename"):
            columns=[r[0] for r in old.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position',('public',table))]
            query=sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(table))
            prior=[]
            for row in old.execute(query):
                values=dict(zip(columns,row))
                if values.get('organization_id')=='planebyte':values['organization_id']=org
                prior.append(values)
            after=[dict(zip(columns,row)) for row in new.execute(query)]
            left=Counter(map(canonical,prior));right=Counter(map(canonical,after))
            if left!=right:
                # Emit only field names/counts, never message content or settings.
                differences[table]={'before_rows':len(prior),'after_rows':len(after),'missing_original_rows':sum((left-right).values()),'added_or_changed_rows':sum((right-left).values())}
            checked.append(table)
    report={'original_tables_checked':len(checked),'original_columns_preserved':not differences,'allowed_value_change':'legacy organization_id planebyte -> persisted PlaneByte UUID only','differences':differences,'source_backup_sha256':result['backup_sha256'],'production_written':False}
    (folder/'history-preservation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if differences:raise SystemExit(1)

if __name__=='__main__':main()
