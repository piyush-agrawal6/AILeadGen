"""Audit all verified historical snapshots; never infer contacted status from a queue."""
import os,json,hashlib
from pathlib import Path
from collections import Counter
from psycopg import sql
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import get_connection
from app.mail.contacted import record,normalize,organization

SENT=('SENT','DELIVERED','REPLIED','POSITIVE_REPLY','BOUNCED')
def run(apply=False):
 c=get_connection(session_bound=True)
 try:
  schemas=[r[0] for r in c.execute("SELECT table_schema FROM information_schema.tables WHERE table_name='email_messages' AND (table_schema='public' OR table_schema LIKE ? OR table_schema LIKE ?) ORDER BY table_schema",('experiment_rollback_%','owner_fresh500_%')).fetchall()]
  messages={};audit=[];unresolved=[];optouts={}
  for schema in schemas:
   def fetch(query):return c.execute(query.format(s=sql.Identifier(schema)).as_string(c.raw)).fetchall()
   has_experiment=bool(c.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=? AND table_name='experiment_members'",(schema,)).fetchone())
   columns="x.campaign_id AS attributed_campaign,x.acquisition_source AS attributed_source,x.reply_disposition" if has_experiment else "NULL AS attributed_campaign,NULL AS attributed_source,NULL AS reply_disposition"
   join=" LEFT JOIN {s}.experiment_members x ON x.message_id=m.id" if has_experiment else ""
   rows=fetch(sql.SQL("SELECT m.*,"+columns+" FROM {s}.email_messages m"+join+" WHERE m.direction='OUTBOUND' AND (m.status IN ('SENT','DELIVERED','REPLIED','POSITIVE_REPLY','BOUNCED') OR EXISTS(SELECT 1 FROM {s}.email_engagement_events e WHERE e.message_id=m.id AND e.event_type='SMTP_ACCEPTED'))"))
   event_rows=fetch(sql.SQL('SELECT message_id,event_type,metadata_json FROM {s}.email_engagement_events'))
   tokens=fetch(sql.SQL("SELECT t.token_hash,t.expires_at,m.to_address,m.test_mode FROM {s}.email_tracking_tokens t JOIN {s}.email_messages m ON m.id=t.message_id WHERE t.action='u' AND m.status='SENT'"))
   for t in tokens:optouts[t['token_hash']]={**dict(t),'email':normalize(t['to_address'])}
   events={}
   for e in event_rows:
    meta=json.loads(e['metadata_json'] or '{}')
    if e['event_type']=='BOUNCED_HARD' and not meta.get('confirmed'):continue
    if e['event_type']=='UNSUBSCRIBED' and meta.get('suppression_applied') is False:continue
    events.setdefault(e['message_id'],set()).add(e['event_type'])
   for raw in rows:
    r=dict(raw);key=r.get('provider_message_id') or r['id'];email=normalize(r['to_address'])
    if not email:raise ValueError('Malformed actual historical recipient in '+schema)
    flags=events.get(r['id'],set())
    m=messages.setdefault(key,{**r,'email':email,'first_at':r.get('sent_at') or r['created_at'],'flags':set()});assert m['email']==email,'Message identity maps to conflicting actual envelope recipients';m['flags']|=flags
    if r.get('reply_disposition')=='POSITIVE':m['flags'].add('POSITIVE_REPLY')
    m['first_at']=min(m['first_at'],r.get('sent_at') or r['created_at'])
   dangling=fetch(sql.SQL("SELECT i.id FROM {s}.outreach_run_items i LEFT JOIN {s}.email_messages m ON m.id=i.message_id WHERE i.status='SENT' AND m.id IS NULL"))
   # A SENT item with no message must be reconciled, never silently skipped.
   unresolved.extend({'schema':schema,'item_id':r[0]} for r in dangling)
   audit.append({'schema':schema,'authoritative_sent_rows':len(rows),'orphan_sent_items':len(dangling)});c.commit()
  import zipfile
  for archive in sorted(Path('data/backups').glob('*.zip')):
   try:
    with zipfile.ZipFile(archive) as z:
     if 'manifest.json' not in z.namelist() or 'db/email_messages.copybin' not in z.namelist():continue
     manifest=json.loads(z.read('manifest.json'));meta=manifest.get('tables',{}).get('email_messages',{});columns=meta.get('columns')
     data=z.read('db/email_messages.copybin');assert hashlib.sha256(data).hexdigest()==meta['sha256'];assert z.testzip() is None
     if columns:names=[x['column_name'] if isinstance(x,dict) else x for x in columns]
     else:
      # Historical email schema is append-only. Binary COPY declares its exact
      # field count; restore only that verified prefix, never guess recipients.
      import struct
      assert data[:11]==b'PGCOPY\n\xff\r\n\x00'
      offset=19+struct.unpack('!i',data[15:19])[0];field_count=struct.unpack('!h',data[offset:offset+2])[0]
      if field_count<0:assert meta['count']==0;continue
      current=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='email_messages' ORDER BY ordinal_position").fetchall()]
      assert 20<=field_count<=len(current);names=current[:field_count]

     c.raw.execute('CREATE TEMP TABLE archived_messages (LIKE public.email_messages INCLUDING DEFAULTS) ON COMMIT DROP')
     with c.raw.cursor().copy(sql.SQL('COPY archived_messages ({}) FROM STDIN (FORMAT BINARY)').format(sql.SQL(',').join(sql.Identifier(n) for n in names))) as copy:copy.write(data)
     count=c.execute('SELECT COUNT(*) FROM archived_messages').fetchone()[0];assert count==meta['count']
     def archive_table(table):
      key='db/'+table+'.copybin'
      if key not in z.namelist():return []
      descriptor=manifest['tables'][table];payload=z.read(key);assert hashlib.sha256(payload).hexdigest()==descriptor['sha256']
      columns=descriptor.get('columns')
      if columns:fields=[x['column_name'] if isinstance(x,dict) else x for x in columns]
      else:
       import struct
       offset=19+struct.unpack('!i',payload[15:19])[0];n=struct.unpack('!h',payload[offset:offset+2])[0]
       if n<0:assert descriptor['count']==0;return []
       fields=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position",(table,)).fetchall()][:n]
      tmp='archive_'+table;c.raw.execute(sql.SQL('CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP').format(sql.Identifier(tmp),sql.Identifier('public',table)))
      with c.raw.cursor().copy(sql.SQL('COPY {} ({}) FROM STDIN (FORMAT BINARY)').format(sql.Identifier(tmp),sql.SQL(',').join(sql.Identifier(x) for x in fields))) as copy:copy.write(payload)
      rows=c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(tmp)).as_string(c.raw)).fetchall();assert len(rows)==descriptor['count'];return rows
     old_events=archive_table('email_engagement_events');old_tokens=archive_table('email_tracking_tokens');by_message={}
     for e in old_events:
      flags=json.loads(e['metadata_json'] or '{}')
      if e['event_type']=='BOUNCED_HARD' and not flags.get('confirmed'):continue
      if e['event_type']=='UNSUBSCRIBED' and flags.get('suppression_applied') is False:continue
      by_message.setdefault(e['message_id'],set()).add(e['event_type'])

     rows=c.execute("SELECT * FROM archived_messages WHERE direction='OUTBOUND' AND status IN ('SENT','DELIVERED','REPLIED','POSITIVE_REPLY','BOUNCED')").fetchall()
     sent_by_id={r['id']:r for r in rows}
     for t in old_tokens:
      m=sent_by_id.get(t['message_id'])
      if m and t['action']=='u':optouts[t['token_hash']]={**dict(t),'email':normalize(m['to_address']),'test_mode':m['test_mode']}
     for raw in rows:
      r=dict(raw);key=r.get('provider_message_id') or r['id'];email=normalize(r['to_address']);assert email
      if key in messages:assert messages[key]['email']==email
      else:messages[key]={**r,'email':email,'first_at':r.get('sent_at') or r['created_at'],'flags':set()}
      messages[key]['flags']|=by_message.get(r['id'],set())
     audit.append({'archive':archive.name,'authoritative_sent_rows':len(rows),'checksum_and_row_count_verified':True});c.commit()
   except zipfile.BadZipFile:
    audit.append({'archive':archive.name,'incomplete_not_used':True})
  gmail=Path('data/backups/contacted-gmail-sent-audit-20261103.json')
  if not gmail.exists():raise ValueError('Complete the authenticated provider Sent audit before cleanup.')
  provider_rows=json.loads(gmail.read_text())
  for r in provider_rows:
   key=r['provider_message_id'];email=normalize(r['to_address']);assert email
   if key in messages:assert messages[key]['email']==email
   else:messages[key]={**r,'id':'provider:'+hashlib.sha256(key.encode()).hexdigest(),'email':email,'first_at':r['sent_at'],'flags':set()}
  audit.append({'provider':'GMAIL_SENT','authoritative_sent_rows':len(provider_rows)})
  assert not unresolved,{'unresolved_actual_send_evidence':unresolved}
  recipients={r['email'] for r in messages.values()}
  if apply:
   for key,m in messages.items():
    f=m['flags'];record(c,message_id=m['id'],email=m['to_address'],sent_at=m['first_at'],provider_message_id=m.get('provider_message_id'),campaign_id=m.get('campaign_id') or m.get('attributed_campaign'),acquisition_source=m.get('attributed_source'),source='HISTORICAL_BACKFILL',flags={'ever_replied':bool({'REPLIED_VERIFIED','POSITIVE_REPLY'}&f),'ever_positive_reply':'POSITIVE_REPLY' in f,'hard_bounced':'BOUNCED_HARD' in f,'unsubscribed':'UNSUBSCRIBED' in f})
   for token,t in optouts.items():
    if t['email']:c.execute('INSERT INTO contacted_unsubscribe_tokens(token_hash,organization_id,normalized_email,expires_at,test_mode) VALUES(?,?,?,?,?) ON CONFLICT(token_hash) DO NOTHING',(token,organization(),t['email'],t['expires_at'],t['test_mode']))
   actual={r[0] for r in c.execute('SELECT normalized_email FROM contacted_recipients WHERE organization_id=?',(organization(),)).fetchall()};ledger=c.execute('SELECT COUNT(*) FROM contacted_recipient_sends WHERE organization_id=?',(organization(),)).fetchone()[0]
   assert actual==recipients,{'missing':len(recipients-actual),'unexpected':len(actual-recipients)};assert ledger==len(messages)
   assert c.execute('SELECT SUM(send_count) FROM contacted_recipients WHERE organization_id=?',(organization(),)).fetchone()[0]==len(messages);c.commit()
  result={'organization_id':organization(),'historical_actual_sends':len(messages),'unique_actual_recipients':len(recipients),'registry_rows':len(recipients) if apply else None,'mismatch':0 if apply else None,'source_audit':audit,'applied':apply,'actual_envelope_used':True,'drafts_queued_unsent_excluded':True};Path('docs/contacted-history-backfill.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 finally:c.close()
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args();run(a.apply)
