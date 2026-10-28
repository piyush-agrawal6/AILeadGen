"""Structured DSN interpretation. Subject/body words never prove a bounce."""
import re
from email.utils import getaddresses,parsedate_to_datetime
from datetime import datetime,timedelta,timezone
from app.mail import tracking
from app.mail.config import mail_settings
from app.database.prospects import now


def parse_dsn(message):
    if message.get_content_type()!='multipart/report' or message.get_param('report-type')!='delivery-status':return None
    refs=set(re.findall(r'<[^<>\s]+>',str(message.get('References',''))+' '+str(message.get('In-Reply-To',''))+' '+str(message.get('Original-Message-ID',''))))
    recipients=[]
    for part in message.walk():
        if part.get_content_type() in ('message/rfc822','text/rfc822-headers'):
            nested=part.get_payload()
            if isinstance(nested,list):
                for item in nested:refs.update(re.findall(r'<[^<>\s]+>',str(item.get('Message-ID',''))))
            elif isinstance(nested,str):refs.update(re.findall(r'(?im)^Message-ID:\s*(<[^<>\s]+>)',nested))
        if part.get_content_type()=='message/delivery-status':
            for block in part.get_payload():
                refs.update(re.findall(r'<[^<>\s]+>',str(block.get('Original-Message-ID',''))))
                recipient=str(block.get('Final-Recipient','') or block.get('Original-Recipient','')).split(';')[-1].strip().lower()
                action=str(block.get('Action','')).lower();status=str(block.get('Status','')).strip()
                if recipient and action in ('failed','delayed') and re.fullmatch(r'[45]\.\d{1,3}\.\d{1,3}',status):recipients.append({'recipient':recipient,'action':action,'status':status})
    return {'kind':'dsn','references':list(refs),'recipients':recipients[:10]}


def process(c,incoming):
    if not tracking.preferences(c)['track_bounces']:return 0
    from app.mail.service import authenticated_reply,ACCOUNT
    refs=incoming.get('references',[])[:30]
    if not refs or not re.fullmatch(r'<[^<>\s]{3,250}>',incoming.get('message_id','')):return 0
    targets={value.lower() for _,value in getaddresses([incoming.get('to','')])}
    if mail_settings().from_address.lower() not in targets:return 0
    rows=c.execute("SELECT * FROM email_messages WHERE direction='OUTBOUND' AND status='SENT' AND account_id=? AND provider_message_id IN ("+','.join('?' for _ in refs)+')',[ACCOUNT,*refs]).fetchall()
    count=0
    for dsn in incoming.get('recipients',[])[:10]:
        candidates=[r for r in rows if r['to_address'].lower()==dsn['recipient']]
        if len(candidates)!=1:continue
        row=candidates[0]
        try:
            when=parsedate_to_datetime(incoming['date'])
            if when.tzinfo is None:continue
            if when<datetime.fromisoformat(row['created_at'])-timedelta(minutes=10) or when>datetime.now(timezone.utc)+timedelta(minutes=10):continue
        except (KeyError,TypeError,ValueError):continue
        # 5.2.2 mailbox full remains temporary even when a server labels it permanent.
        hard=dsn['action']=='failed' and (dsn['status'].startswith('5.1.') or dsn['status']=='5.2.1')
        kind='BOUNCED_HARD' if hard else 'BOUNCED_SOFT';confirmed=authenticated_reply(incoming)
        inserted=tracking.event(c,row['id'],kind,dedup='dsn:'+incoming['message_id']+':'+row['id'],metadata={'status':dsn['status'],'action':dsn['action'],'confirmed':confirmed,'suppression_applied':confirmed and not row['test_mode']})
        if not inserted:continue
        count+=1
        if not confirmed or row['test_mode']:continue
        address=dsn['recipient'];previous=c.execute('SELECT soft_bounce_count,status FROM email_address_suppressions WHERE address=?',(address,)).fetchone()
        soft=(previous['soft_bounce_count'] if previous else 0)+(0 if hard else 1)
        status='INVALID' if hard or previous and previous['status']=='INVALID' else 'TEMPORARILY_UNUSABLE' if soft>=mail_settings().soft_bounce_threshold else 'REVIEW'
        c.execute("INSERT INTO email_address_suppressions VALUES(?,?,?,?,?) ON CONFLICT(address) DO UPDATE SET source=excluded.source,soft_bounce_count=excluded.soft_bounce_count,status=excluded.status,updated_at=excluded.updated_at",(address,'HARD_BOUNCE' if hard else 'OTHER',soft,status,now()))
        if status=='INVALID':c.execute("UPDATE contacts SET is_valid=0 WHERE lower(contact_value)=? AND contact_type='email'",(address,))
    return count
