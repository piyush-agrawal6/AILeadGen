"""Exact-address permanent history. No recipient is registered before acceptance."""
import os,re,uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from app.database.contactable_schema import ready

def organization():
    from app.platform.context import organization as active_organization
    return active_organization()

def normalize(value):
    email=str(value or '').strip().lower()
    return email if len(email)<=254 and re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",email) else None

def lookup(c,email,*,organization_id=None):
    email=normalize(email)
    if not email or not ready(c):return None
    from app.platform.context import organization as active_organization
    org=active_organization(organization_id)
    return c.execute('SELECT * FROM contacted_recipients WHERE organization_id=? AND normalized_email=?',(org,email)).fetchone()

def ensure_new(c,email,*,idempotency_key=None,organization_id=None):
    email=normalize(email)
    if not email:raise HTTPException(422,'A valid business email is required.')
    if not ready(c):return
    own=c.execute('SELECT id,to_address,status FROM email_messages WHERE idempotency_key=?',(idempotency_key,)).fetchone() if idempotency_key else None
    if lookup(c,email,organization_id=organization_id) and not(own and normalize(own['to_address'])==email and own['status']=='SENT'):
        raise HTTPException(409,'ALREADY_CONTACTED: this organization has already emailed this address.')
    pending=c.execute("SELECT id,idempotency_key FROM email_messages WHERE organization_id=? AND LOWER(TRIM(to_address))=? AND direction='OUTBOUND' AND status IN ('SENDING','UNCERTAIN')",(organization_id or organization(),email)).fetchall()
    if any(r['idempotency_key']!=idempotency_key for r in pending):raise HTTPException(409,'An existing or uncertain send already reserves this address.')

def record(c,*,message_id,email,sent_at,provider_message_id=None,campaign_id=None,acquisition_source=None,company_name=None,company_domain=None,organization_id=None,source='LIVE_SEND',flags=None,status='SENT'):
    if not ready(c):return False
    original=str(email).strip();email=normalize(email)
    if not email:raise ValueError('Actual sent recipient is malformed; reconcile before clearing history.')
    parsed=datetime.fromisoformat(sent_at);sent_at=(parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()
    from app.platform.context import organization as active_organization
    org=active_organization(organization_id);stamp=datetime.now(timezone.utc).isoformat();key=provider_message_id or message_id
    if not key or not sent_at:raise ValueError('Actual outbound message identity and send timestamp are required.')
    added=c.execute('INSERT INTO contacted_recipient_sends(organization_id,message_key,normalized_email,message_id,provider_message_id,sent_at,campaign_id,acquisition_source,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,message_key) DO NOTHING',(org,key,email,message_id,provider_message_id,sent_at,campaign_id,acquisition_source,stamp)).rowcount
    if not added:
        prior=c.execute('SELECT normalized_email FROM contacted_recipient_sends WHERE organization_id=? AND message_key=?',(org,key)).fetchone()
        if prior[0]!=email:raise ValueError('Actual message identity conflicts with its recorded recipient.')
    flags=flags or {};rid=str(uuid.uuid5(uuid.NAMESPACE_URL,org+':contacted:'+email))
    c.execute('''INSERT INTO contacted_recipients(id,organization_id,normalized_email,original_email,canonical_domain,company_name,company_domain,first_sent_at,last_sent_at,send_count,first_campaign_id,last_campaign_id,first_message_id,last_message_id,first_acquisition_source,last_acquisition_source,last_delivery_status,ever_replied,ever_positive_reply,hard_bounced,unsubscribed,do_not_contact,source,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,normalized_email) DO UPDATE SET
      first_campaign_id=CASE WHEN excluded.first_sent_at<contacted_recipients.first_sent_at THEN excluded.first_campaign_id ELSE contacted_recipients.first_campaign_id END,
      first_message_id=CASE WHEN excluded.first_sent_at<contacted_recipients.first_sent_at THEN excluded.first_message_id ELSE contacted_recipients.first_message_id END,
      first_acquisition_source=CASE WHEN excluded.first_sent_at<contacted_recipients.first_sent_at THEN excluded.first_acquisition_source ELSE contacted_recipients.first_acquisition_source END,
      last_campaign_id=CASE WHEN excluded.last_sent_at>=contacted_recipients.last_sent_at THEN excluded.last_campaign_id ELSE contacted_recipients.last_campaign_id END,
      last_message_id=CASE WHEN excluded.last_sent_at>=contacted_recipients.last_sent_at THEN excluded.last_message_id ELSE contacted_recipients.last_message_id END,
      last_acquisition_source=CASE WHEN excluded.last_sent_at>=contacted_recipients.last_sent_at THEN excluded.last_acquisition_source ELSE contacted_recipients.last_acquisition_source END,
      first_sent_at=CASE WHEN contacted_recipients.first_sent_at<excluded.first_sent_at THEN contacted_recipients.first_sent_at ELSE excluded.first_sent_at END,last_sent_at=CASE WHEN contacted_recipients.last_sent_at>excluded.last_sent_at THEN contacted_recipients.last_sent_at ELSE excluded.last_sent_at END,
      send_count=contacted_recipients.send_count+excluded.send_count,ever_replied=CASE WHEN contacted_recipients.ever_replied>excluded.ever_replied THEN contacted_recipients.ever_replied ELSE excluded.ever_replied END,
      ever_positive_reply=CASE WHEN contacted_recipients.ever_positive_reply>excluded.ever_positive_reply THEN contacted_recipients.ever_positive_reply ELSE excluded.ever_positive_reply END,hard_bounced=CASE WHEN contacted_recipients.hard_bounced>excluded.hard_bounced THEN contacted_recipients.hard_bounced ELSE excluded.hard_bounced END,
      unsubscribed=CASE WHEN contacted_recipients.unsubscribed>excluded.unsubscribed THEN contacted_recipients.unsubscribed ELSE excluded.unsubscribed END,do_not_contact=CASE WHEN contacted_recipients.do_not_contact>excluded.do_not_contact THEN contacted_recipients.do_not_contact ELSE excluded.do_not_contact END,updated_at=excluded.updated_at''',
      (rid,org,email,original,email.rsplit('@',1)[1],company_name,company_domain,sent_at,sent_at,1 if added else 0,campaign_id,campaign_id,message_id,message_id,acquisition_source,acquisition_source,status,int(flags.get('ever_replied',False)),int(flags.get('ever_positive_reply',False)),int(flags.get('hard_bounced',False)),int(flags.get('unsubscribed',False)),int(flags.get('do_not_contact',False)),source,stamp,stamp))
    return bool(added)

def record_message(c,message_id):
    if not ready(c):return
    org=organization()
    r=c.execute("SELECT * FROM email_messages WHERE id=? AND organization_id=? AND direction='OUTBOUND' AND status='SENT'",(message_id,org)).fetchone()
    if not r:return
    b=c.execute('SELECT b.name,b.domain,s.source_type FROM businesses b JOIN pipeline_runs p ON p.id=b.run_id LEFT JOIN scan_campaigns s ON s.id=p.campaign_id WHERE b.prospect_id=? ORDER BY b.id DESC LIMIT 1',(r['prospect_id'],)).fetchone()
    source=c.execute('SELECT source_type FROM scan_campaigns WHERE id=?',(r['campaign_id'],)).fetchone() if r['campaign_id'] else None
    record(c,message_id=r['id'],email=r['to_address'],sent_at=r['sent_at'] or r['created_at'],provider_message_id=r['provider_message_id'],campaign_id=r['campaign_id'],acquisition_source=source[0] if source else b['source_type'] if b else None,company_name=b['name'] if b else None,company_domain=b['domain'] if b else None,organization_id=r['organization_id'])
    for token in c.execute("SELECT token_hash,expires_at FROM email_tracking_tokens WHERE message_id=? AND action='u'",(message_id,)).fetchall():
        c.execute('INSERT INTO contacted_unsubscribe_tokens(token_hash,organization_id,normalized_email,expires_at,test_mode) VALUES(?,?,?,?,?) ON CONFLICT(token_hash) DO NOTHING',(token['token_hash'],r['organization_id'],normalize(r['to_address']),token['expires_at'],r['test_mode']))

def engagement(c,message_id,event_type):
    if not ready(c):return
    r=c.execute('SELECT organization_id,to_address FROM email_messages WHERE id=? AND organization_id=?',(message_id,organization())).fetchone()
    fields={'REPLIED_VERIFIED':'ever_replied','BOUNCED_HARD':'hard_bounced','UNSUBSCRIBED':'unsubscribed','POSITIVE_REPLY':'ever_positive_reply'}
    if r and event_type in fields:c.execute('UPDATE contacted_recipients SET '+fields[event_type]+'=1,updated_at=? WHERE organization_id=? AND normalized_email=?',(datetime.now(timezone.utc).isoformat(),r['organization_id'],normalize(r['to_address'])))


def usage(c,since):
    """Counts accepted history even after operational messages are reset."""
    org=organization()
    if not ready(c):return c.execute("SELECT COUNT(*) FROM email_messages m JOIN prospects p ON p.id=m.prospect_id WHERE p.organization_id=? AND m.direction='OUTBOUND' AND m.status IN ('SENT','SENDING','UNCERTAIN') AND m.created_at>=?",(org,since)).fetchone()[0]
    org=organization();past=c.execute('SELECT COUNT(*) FROM contacted_recipient_sends WHERE organization_id=? AND sent_at>=?',(org,since)).fetchone()[0]
    current=c.execute("SELECT COUNT(*) FROM email_messages m WHERE m.organization_id=? AND m.direction='OUTBOUND' AND m.status IN ('SENT','SENDING','UNCERTAIN') AND m.created_at>=? AND NOT EXISTS(SELECT 1 FROM contacted_recipient_sends h WHERE h.organization_id=m.organization_id AND (h.message_id=m.id OR h.provider_message_id=m.provider_message_id))",(org,since)).fetchone()[0]
    return past+current


def known_addresses(c,emails):
    values=sorted({v for e in emails if (v:=normalize(e))})
    if not values or not ready(c):return set()
    return {r[0] for r in c.execute('SELECT normalized_email FROM contacted_recipients WHERE organization_id=? AND normalized_email IN ('+','.join('?' for _ in values)+')',[organization(),*values]).fetchall()}

def archived_reply(c,incoming):
    """Retain verified reply/suppression flags after an owner archives live threads.

    Never reconstruct a prospect, conversation or email body from historical data.
    """
    if not ready(c) or incoming.get('automatic'):return False
    from app.mail.service import authenticated_reply
    from app.mail.config import mail_settings
    from email.utils import getaddresses,parsedate_to_datetime
    from datetime import timedelta
    if not authenticated_reply(incoming):return False
    refs=list(dict.fromkeys(incoming.get('references',[])))[:30]
    senders=getaddresses([incoming.get('from','')]);targets={normalize(v) for _,v in getaddresses([incoming.get('to','')])}
    if not refs or len(senders)!=1 or normalize(mail_settings().from_address) not in targets:return False
    email=normalize(senders[0][1]);org=organization()
    rows=c.execute('SELECT sent_at FROM contacted_recipient_sends WHERE organization_id=? AND normalized_email=? AND provider_message_id IN ('+','.join('?' for _ in refs)+')',[org,email,*refs]).fetchall()
    if not rows:return False
    try:
        date=parsedate_to_datetime(incoming['date']);date=date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        first=min(datetime.fromisoformat(r['sent_at']) for r in rows)
        if date<first-timedelta(minutes=10) or date>datetime.now(timezone.utc)+timedelta(minutes=10):return False
    except (ValueError,TypeError,KeyError):return False
    from app.experiments.service import classify
    disposition=classify(incoming.get('body_text',''));stamp=datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE contacted_recipients SET ever_replied=1,ever_positive_reply=CASE WHEN ?=1 THEN 1 ELSE ever_positive_reply END,unsubscribed=CASE WHEN ?=1 THEN 1 ELSE unsubscribed END,do_not_contact=CASE WHEN ?=1 THEN 1 ELSE do_not_contact END,last_delivery_status='REPLIED',updated_at=? WHERE organization_id=? AND normalized_email=?",(int(disposition=='POSITIVE'),int(disposition=='UNSUBSCRIBE'),int(disposition=='UNSUBSCRIBE'),stamp,org,email))
    if disposition=='UNSUBSCRIBE':c.execute("INSERT INTO email_address_suppressions(address,source,status,updated_at,organization_id) VALUES(?,'VERIFIED_ARCHIVED_REPLY','INVALID',?,?) ON CONFLICT(address) DO UPDATE SET status='INVALID',source='VERIFIED_ARCHIVED_REPLY',updated_at=excluded.updated_at WHERE email_address_suppressions.organization_id=excluded.organization_id",(email,stamp,org))
    return True
