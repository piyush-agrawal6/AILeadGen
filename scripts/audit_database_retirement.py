"""Read-only retirement inventory. Store metadata/counts privately, never row contents.

Pass the selected DSN via RETIREMENT_AUDIT_DSN. One consistent read-only snapshot
per database; an inaccessible table is not evidence that it is empty.
"""
import argparse,json,os
from pathlib import Path
import psycopg
from psycopg import sql

def collect(c):
    c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
    c.execute("SET LOCAL statement_timeout='15s'")
    scope="n.nspname NOT IN ('information_schema','pg_catalog') AND n.nspname !~ '^pg_'"
    relations=c.execute('SELECT n.nspname,t.relname,t.relkind,t.relrowsecurity FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace WHERE '+scope+" AND t.relkind IN ('r','p','v','m','S','f') ORDER BY 1,2").fetchall()
    counts={}
    tables=[(s,n) for s,n,k,_ in relations if k in ('r','p')]
    for i in range(0,len(tables),24):
        batch=tables[i:i+24]
        query=sql.SQL(' UNION ALL ').join(sql.SQL('SELECT {} AS relation,count(*) FROM {}').format(sql.Literal(s+'.'+t),sql.Identifier(s,t)) for s,t in batch)
        counts.update(c.execute(query).fetchall())
    constraints=c.execute('SELECT n.nspname,t.relname,k.conname,k.contype,d.nspname,f.relname,k.confdeltype FROM pg_constraint k JOIN pg_class t ON t.oid=k.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace LEFT JOIN pg_class f ON f.oid=k.confrelid LEFT JOIN pg_namespace d ON d.oid=f.relnamespace WHERE '+scope+' ORDER BY 1,2,3').fetchall()
    return dict(relations=relations,row_counts=counts,constraints=constraints,
                indexes=c.execute('SELECT schemaname,tablename,indexname FROM pg_indexes WHERE schemaname NOT IN (\'information_schema\',\'pg_catalog\') ORDER BY 1,2,3').fetchall(),
                triggers=c.execute('SELECT n.nspname,t.relname,g.tgname,g.tgisinternal FROM pg_trigger g JOIN pg_class t ON t.oid=g.tgrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE '+scope+' ORDER BY 1,2,3').fetchall(),
                functions=c.execute('SELECT n.nspname,p.proname,p.prokind FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE '+scope+' ORDER BY 1,2,3').fetchall(),
                policies=c.execute('SELECT schemaname,tablename,policyname FROM pg_policies ORDER BY 1,2,3').fetchall(),
                grants=c.execute("SELECT table_schema,table_name,grantee,privilege_type FROM information_schema.role_table_grants WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2,3,4").fetchall())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);args=p.parse_args();os.umask(0o077)
    with psycopg.connect(os.environ['RETIREMENT_AUDIT_DSN'],connect_timeout=10) as c:result=collect(c)
    with args.output.open('x') as f:json.dump(result,f,separators=(',',':'))
