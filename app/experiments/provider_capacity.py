"""Conservative account-wide Sent accounting; Gmail exposes no remaining quota API."""
import json,re,time,imaplib
from datetime import datetime,timezone,timedelta
from email.parser import BytesParser
from email import policy
from app.experiments.plan import EXPERIMENT_ID

def refresh(c,*,force=False):
 row=c.execute('SELECT configuration_json FROM experiments WHERE id=?',(EXPERIMENT_ID,)).fetchone()
 if not row:return None
 config=json.loads(row[0]);stamp=datetime.now(timezone.utc)
 previous=config.get('provider_preflight_at')
 if previous and not force and stamp-datetime.fromisoformat(previous)<timedelta(minutes=45):return config.get('provider_sent_count')
 from app.mail.providers import provider
 p=provider();client=None
 try:
  client=p.imap();status,_=client.select(p.sent_mailbox(client),readonly=True)
  if status!='OK':raise RuntimeError('Sent folder could not be selected.')
  # IMAP SINCE is date-granular; INTERNALDATE below enforces a true rolling24h.
  status,raw=client.uid('search',None,'SINCE',(stamp-timedelta(days=2)).strftime('%d-%b-%Y'))
  if status!='OK':raise RuntimeError('Sent accounting search failed.')
  ids=raw[0].split() if raw and raw[0] else []
  if len(ids)>1500:raise RuntimeError('Sent accounting exceeded its safe bounded batch size.')
  known={r[0] for r in c.execute("SELECT provider_message_id FROM email_messages WHERE direction='OUTBOUND' AND created_at>=?",((stamp-timedelta(days=3)).isoformat(),)).fetchall()}
  untracked=[];count=0
  for start in range(0,len(ids),50):
   status,parts=client.uid('fetch',b','.join(ids[start:start+50]),'(INTERNALDATE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
   if status!='OK':raise RuntimeError('Sent accounting fetch failed.')
   for part in parts:
    if not isinstance(part,tuple):continue
    internal=imaplib.Internaldate2tuple(part[0])
    if not internal:raise RuntimeError('Sent timestamp could not be verified.')
    sent=datetime.fromtimestamp(time.mktime(internal),timezone.utc)
    if sent<stamp-timedelta(hours=24):continue
    count+=1;mid=str(BytesParser(policy=policy.default).parsebytes(part[1]).get('Message-ID',''))
    if mid not in known:untracked.append(sent.isoformat())
  config.update(provider_preflight_at=stamp.isoformat(),provider_sent_count=count,untracked_sent_at=untracked,provider_capacity_verified=True)
  c.execute('UPDATE experiments SET configuration_json=?,updated_at=? WHERE id=?',(json.dumps(config),stamp.isoformat(),EXPERIMENT_ID));return count
 finally:
  if client:
   try:client.logout()
   except Exception:pass
