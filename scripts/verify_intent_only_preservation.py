"""Read-only production table/grant preservation check; no migration or cleanup."""
import json,subprocess
from pathlib import Path
from dotenv import dotenv_values
from app.database.postgres import PostgresConnection
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/artifacts/verification/intent-only'
def main():
    baseline=json.loads((OUT/'database-baseline.json').read_text())
    c=PostgresConnection(dotenv_values(ROOT/'.env',interpolate=False)['DATABASE_URL'],session_bound=True)
    try:
        c.execute('BEGIN READ ONLY')
        tables=[r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()]
        counts={table:c.execute('SELECT COUNT(*) FROM "'+table+'"').fetchone()[0] for table in baseline['lead_engine_related_counts']}
        grants=[dict(r) for r in c.execute("SELECT organization_id,product,enabled FROM organization_products WHERE product='LEADGEN' ORDER BY organization_id").fetchall()]
        schema=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        missing=sorted(set(baseline['tables'])-set(tables));decreased={t:{'before':n,'after':counts[t]} for t,n in baseline['lead_engine_related_counts'].items() if counts[t]<n}
        if missing or decreased or schema!=baseline['schema'] or grants!=baseline['stored_lead_engine_entitlements']:raise RuntimeError('Preservation mismatch; inspect read-only evidence before any further release.')
        owner=[dict(r) for r in c.execute("SELECT o.id,o.name,m.role,m.status FROM organizations o JOIN organization_memberships m ON m.organization_id=o.id WHERE m.user_id='planebyte@gmail.com' AND m.status='ACTIVE' AND o.id='e5ffc3dc-241e-5558-acd4-84f5fe354ca7'").fetchall()]
        if len(owner)!=1 or owner[0]['role'] not in ('OWNER','ADMIN'):raise RuntimeError('Approved owner workspace cannot be verified.')
        events=[]
        columns=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='billing_webhook_events'").fetchall()]
        # Only status metadata is inspected; raw financial payloads stay private.
        if 'event_type' in columns and 'status' in columns:
            order=next((column for column in ('received_at','created_at','id') if column in columns),None)
            events=[dict(r) for r in c.execute('SELECT event_type,status FROM billing_webhook_events'+(' ORDER BY '+order+' DESC' if order else '')+' LIMIT 10').fetchall()]
        proof={'read_only':True,'schema':schema,'original_tables':len(baseline['tables']),'present_tables':len(tables),'missing_tables':missing,'lead_related_tables':len(counts),'counts':counts,'decreased_counts':decreased,'stored_grants_unchanged':True,'verified_owner':owner,'recent_billing_event_states':events}
    finally:c.rollback();c.close()
    source=json.loads((OUT/'source-baseline.json').read_text())
    deleted=subprocess.check_output(['git','diff','--diff-filter=D','--name-only',source['starting_commit'],'HEAD'],cwd=ROOT,text=True).strip()
    if deleted:raise RuntimeError('Tracked source deletion found.')
    proof.update(starting_commit=source['starting_commit'],deletions=[],restoration='Approved configuration-only release; no features or data need recovery')
    p=OUT/'preservation-final.json';p.write_text(json.dumps(proof,indent=2));p.chmod(0o600)
    print(json.dumps({'schema':schema,'all_original_tables_preserved':True,'lead_related_table_counts_preserved':True,'stored_grants_preserved':True,'tracked_file_deletions':0,'owner_verified':True}))
if __name__=='__main__':main()
