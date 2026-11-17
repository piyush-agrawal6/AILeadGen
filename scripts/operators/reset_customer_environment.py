"""Owner-authorized P0 customer reset, with exact snapshot/rehearsal gates.

No DROP/TRUNCATE, schema/credential changes, financial action or provider call.
Protected financial/security/suppression records and their minimal FK parents stay.
All customer deletion targets are materialized under one exclusive transaction.
"""
import argparse,hashlib,json,os,re
from pathlib import Path
import psycopg
from psycopg import sql
from dotenv import dotenv_values
from app.database.postgres import session_url


SYSTEM={'schema_migrations','billing_plan_mappings','scan_markets','experiment_catalog','provider_rate_limits','intent_provider_limits','worker_health','intent_worker_health','internal_request_nonces','recovery_checkpoints'}
PROTECTED={'billing_payments','billing_subscriptions','billing_customers','billing_webhook_events','payu_access_orders','payu_access_refunds','payu_access_callback_events','payu_access_refunds','payu_refund_observations','commercial_contracts','audit_log','account_security_events','account_privacy_requests','account_terms_acceptances','email_address_suppressions','customer_mail_suppressions','transactional_suppressions','contacted_recipients','contacted_recipient_sends','contacted_unsubscribe_tokens','deletion_batches','deletion_targets'}
ZERO={'customer_accounts','customer_sessions','account_admissions','account_link_tickets','account_login_tickets','account_verifications','account_recovery_requests','account_recovery_tokens','organization_memberships','workspace_invitations','workspace_api_keys','organization_integrations','customer_gmail_connections','acquisition_google_connections','ideal_customer_profiles','organization_profiles','organization_services','intent_signals','intent_monitors','intent_opportunities','growth_research','access_periods','launch_trial_claims','customer_workspace_access'}
AUTHORIZATION='owner-final-p0-customer-reset-20261116'

def schema(c):
 tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
 fks=[]
 for child,parent,cols,refs in c.execute("""SELECT a.relname,b.relname,
 ARRAY(SELECT attname FROM unnest(k.conkey) WITH ORDINALITY u(attnum,n) JOIN pg_attribute x ON x.attrelid=k.conrelid AND x.attnum=u.attnum ORDER BY n),
 ARRAY(SELECT attname FROM unnest(k.confkey) WITH ORDINALITY u(attnum,n) JOIN pg_attribute x ON x.attrelid=k.confrelid AND x.attnum=u.attnum ORDER BY n)
 FROM pg_constraint k JOIN pg_class a ON a.oid=k.conrelid JOIN pg_class b ON b.oid=k.confrelid WHERE k.contype='f' AND k.connamespace='public'::regnamespace ORDER BY a.relname,b.relname"""):
  fks.append({'child':child,'parent':parent,'columns':cols,'references':refs})
 nullable={(t,col) for t,col in c.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND is_nullable='YES'")}
 return tables,fks,nullable

def queued(c,statements):
 # All statements remain parameter-bound and on the same locked transaction.
 # A single network flush avoids minutes of cross-region lock-held idle time.
 with c.pipeline():cursors=[c.execute(q,args) for q,args in statements]
 return cursors

def fingerprint(c,tables):
 queries=[]
 for table in tables:
  q=sql.SQL("SELECT COUNT(*),encode(sha256(convert_to(COALESCE(string_agg(digest,chr(10) ORDER BY digest),''),'UTF8')),'hex') FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') digest FROM {} t) records").format(sql.Identifier(table))
  queries.append((q,()))
 return {t:dict(zip(('count','sha256'),cursor.fetchone())) for t,cursor in zip(tables,queued(c,queries))}

def reset(c,*,commit=False):
 tables,fks,nullable=schema(c)
 if not (SYSTEM|PROTECTED|ZERO)<=set(tables):raise RuntimeError('Expected reset table inventory changed')
 c.execute("SET LOCAL lock_timeout='15s'");c.execute("SET LOCAL statement_timeout='60s'")
 c.execute(sql.SQL('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in tables)))
 before=fingerprint(c,tables)
 keep={t:'reset_keep_'+str(i) for i,t in enumerate(tables)}
 setup=[]
 for t in tables:
  setup.append((sql.SQL('CREATE TEMP TABLE {} (row_tid tid PRIMARY KEY) ON COMMIT DROP').format(sql.Identifier(keep[t])),()))
  if t in SYSTEM|PROTECTED:setup.append((sql.SQL('INSERT INTO {} SELECT ctid FROM {}').format(sql.Identifier(keep[t]),sql.Identifier(t)),()))
 queued(c,setup)
 # Preserve only parent rows actually required by a protected record, recursively.
 for iteration in range(len(tables)+1):
  queries=[]
  for fk in fks:
   joins=sql.SQL(' AND ').join(sql.SQL('ch.{}=pa.{}').format(sql.Identifier(a),sql.Identifier(b)) for a,b in zip(fk['columns'],fk['references']))
   q=sql.SQL('INSERT INTO {} SELECT DISTINCT pa.ctid FROM {} ch JOIN {} k ON k.row_tid=ch.ctid JOIN {} pa ON {} ON CONFLICT DO NOTHING').format(sql.Identifier(keep[fk['parent']]),sql.Identifier(fk['child']),sql.Identifier(keep[fk['child']]),sql.Identifier(fk['parent']),joins)
   queries.append((q,()))
  inserted=sum(cur.rowcount for cur in queued(c,queries))
  if not inserted:break
 else:raise RuntimeError('Protected parent closure did not converge')
 counts=queued(c,[(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(keep[t])),()) for t in tables])
 targets={t:before[t]['count']-cur.fetchone()[0] for t,cur in zip(tables,counts)}
 if any(before[t]['count']-targets[t] for t in ZERO):raise RuntimeError('A protected record requires a live customer authentication/resource row; isolate that exception before resetting')
 # Nullable pointers in records being removed can be cleared to break cycles.
 # Their primary keys and the protected records remain unchanged.
 updates=[]
 for fk in fks:
  t=fk['child'];column=next((x for x in fk['columns'] if (t,x) in nullable),None)
  if column and targets[t]:
   updates.append((sql.SQL('UPDATE {} SET {}=NULL WHERE ctid NOT IN (SELECT row_tid FROM {})').format(sql.Identifier(t),sql.Identifier(column),sql.Identifier(keep[t])),()))
 queued(c,updates)
 # Only populated delete-target edges can block deletion. Empty tables and
 # protected-only children have already been accounted for by parent closure.
 remaining={t for t in tables if targets[t]};deleted={t:0 for t in tables};order=[]
 while remaining:
  ready=sorted(t for t in remaining if not any(f['parent']==t and f['child'] in remaining and f['child']!=t and not any((f['child'],col) in nullable for col in f['columns']) for f in fks))
  if not ready:raise RuntimeError('A non-nullable customer dependency cycle needs explicit handling')
  for t in ready:
   amount=c.execute(sql.SQL('DELETE FROM {} WHERE ctid NOT IN (SELECT row_tid FROM {})').format(sql.Identifier(t),sql.Identifier(keep[t]))).rowcount
   if amount!=targets[t]:raise RuntimeError('Deletion count changed for '+t)
   deleted[t]=amount;order.append(t);remaining.remove(t)
 # FK-required ledger parents are retired, not customer workspaces/accounts.
 # Preserve original IDs for accounting traceability; deny recreation by keeping
 # the old stable ID separate from its retired, undeliverable email address.
 users=c.execute("SELECT id FROM users").fetchall()
 for (key,) in users:
  tombstone='retired+'+hashlib.sha256(key.encode()).hexdigest()[:32]+'@invalid.example'
  c.execute("UPDATE users SET email=%s,display_name='Retired financial reference',avatar_url=NULL,role='VIEWER',provider='RETIRED',last_login=NULL WHERE id=%s",(tombstone,key))
 c.execute("UPDATE organizations SET status='ARCHIVED',name='Retired protected ledger',slug='retired-'||id")
 # Pending provider work/credentials/access never remain in a retained ledger.
 if c.execute("SELECT COUNT(*) FROM customer_sessions WHERE revoked_at IS NULL").fetchone()[0]:raise RuntimeError('An active customer session survived')
 after=fingerprint(c,tables)
 for t in SYSTEM|PROTECTED:
  if before[t]!=after[t]:raise RuntimeError('Protected record content changed: '+t)
 for t in ZERO:
  if after[t]['count']:raise RuntimeError('Customer table not empty: '+t)
 proof={'authorization':AUTHORIZATION,'production_written':commit,'schema_preserved':before['schema_migrations']==after['schema_migrations'],'protected_records_preserved':True,'tables':{t:{'before':before[t]['count'],'deleted':deleted[t],'retained':after[t]['count'],'classification':'SYSTEM' if t in SYSTEM else 'PROTECTED' if t in PROTECTED else 'PROTECTED_FK_REFERENCE' if after[t]['count'] else 'CUSTOMER_RESET'} for t in tables},'deleted_total':sum(deleted.values()),'dependency_delete_order':order,'foreign_keys':fks,'retired_user_references':len(users),'retired_organization_references':after['organizations']['count'],'zero_tables':sorted(ZERO),'before_fingerprints':before,'after_fingerprints':after,'no_drop_truncate_or_migration':True}
 return proof

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=('rehearse','apply'),required=True);p.add_argument('--recovery',required=True);p.add_argument('--output',required=True);args=p.parse_args()
 os.umask(0o077);recovery=json.loads(Path(args.recovery).read_text());backup=Path(recovery['backup'])
 if not recovery.get('restored_exactly') or recovery.get('row_loss') or hashlib.sha256(backup.read_bytes()).hexdigest()!=recovery['backup_sha256']:raise RuntimeError('Exact fresh recovery verification required')
 target='postgresql://planebyte@/'+recovery['local_restore_database']+'?host='+recovery['local_socket']+'&port=15433'
 if args.mode=='apply':
  rehearsal=json.loads(Path(args.output).with_name('reset-rehearsal.json').read_text())
  if rehearsal.get('authorization')!=AUTHORIZATION or not rehearsal.get('protected_records_preserved') or not rehearsal.get('schema_preserved'):raise RuntimeError('Matching completed local reset rehearsal required')
  if rehearsal.get('backup_sha256')!=recovery['backup_sha256']:raise RuntimeError('Rehearsal uses a different backup')
  values=dotenv_values(os.environ['PLANEBYTE_OPERATOR_ENV_FILE'],interpolate=False);target=session_url(values['DATABASE_URL'])
  if not (__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(target).hostname or '').endswith('.neon.tech'):raise RuntimeError('Unexpected production database')
 with psycopg.connect(target,connect_timeout=15) as c:
  proof=reset(c,commit=args.mode=='apply');proof.update(backup_sha256=recovery['backup_sha256'],backup=str(backup),mode=args.mode)
  if args.mode=='rehearse':c.rollback() # Exact dry run; leave restored snapshot intact.
  else:c.commit()
 out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2));out.chmod(0o600)
 print(json.dumps({k:proof[k] for k in ('mode','deleted_total','retired_user_references','retired_organization_references','schema_preserved','protected_records_preserved','production_written')}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'FAILED','error_type':type(e).__name__,'message':str(e) if isinstance(e,RuntimeError) else 'Restricted reset evidence; credentials withheld'}));raise SystemExit(1)
