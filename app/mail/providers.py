"""Verified Hostinger SMTP/IMAP only; no discovery, POP3 or credential logging."""
import imaplib,smtplib,ssl,re,time,hashlib
from datetime import datetime,timezone,timedelta
from email import policy
from email.parser import BytesParser
from typing import Protocol
from bs4 import BeautifulSoup
from app.mail.config import mail_settings

class SendFailed(Exception):pass
class SendUncertain(Exception):pass
class EmailProvider(Protocol):
    def send_message(self,message):...
    def sync_messages(self,known_ids,cursor):...
    def health_check(self):...

def parse_incoming(content,known_ids,automatic_refs=()):
    """Shared bounded MIME parser; persist only messages linked to owned outbound IDs."""
    if not isinstance(content,bytes) or len(content)>524288:return None
    parsed=BytesParser(policy=policy.default).parsebytes(content)
    refs=set(re.findall(r'<[^<>\s]+>',str(parsed.get('In-Reply-To',''))+' '+str(parsed.get('References',''))))
    common={'message_id':str(parsed.get('Message-ID','')),'from':str(parsed.get('From','')),'to':str(parsed.get('To','')),
        'date':str(parsed.get('Date','')),'authentication':str(parsed.get('Authentication-Results',''))}
    if parsed.get_content_type()=='multipart/report' and parsed.get_param('report-type')=='delivery-status':
        from app.mail.bounces import parse_dsn
        dsn=parse_dsn(parsed)
        return {**dsn,**common} if dsn and set(dsn['references']).intersection(known_ids) else None
    if not refs.intersection(known_ids):return None
    automatic=str(parsed.get('Auto-Submitted','no')).lower()!='no'
    if automatic and not refs.intersection(set(automatic_refs)):return None
    body=parsed.get_body(preferencelist=('plain','html')) if parsed.is_multipart() else parsed
    text=''
    if body:
        try:text=body.get_content()
        except Exception:text='Message text unavailable.'
        if body.get_content_type()=='text/html':
            soup=BeautifulSoup(text,'html.parser')
            for node in soup(['script','style','iframe','object']):node.decompose()
            text=soup.get_text(' ',strip=True)
    return {**common,'subject':str(parsed.get('Subject',''))[:300],'references':list(refs),'in_reply_to':str(parsed.get('In-Reply-To','')),
        'body_text':str(text)[:20000],'automatic':automatic}

def special_use_folder(client,flag):
    """Read server-assigned RFC 6154 flags; preserve IMAP UTF-7 wire names."""
    status,rows=client.list()
    if status!='OK':raise RuntimeError('IMAP_FOLDER_LIST_FAILED')
    for item in (rows or [])[:1000]:
        literal=None
        if isinstance(item,tuple):raw,literal=item
        else:raw=item
        if not isinstance(raw,bytes) or len(raw)>8192:continue
        match=re.fullmatch(rb'\((.*?)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(.+)',raw)
        if not match or flag.lower().encode() not in match[1].lower().split():continue
        name=match[2]
        if literal is not None:
            if not re.fullmatch(rb'\{[0-9]+\}',name) or len(literal)>4096:continue
            name=b'"'+literal.replace(b'\\',b'\\\\').replace(b'"',b'\\"')+b'"'
        if b'\r' in name or b'\n' in name or len(name)>4096:continue
        if not (re.fullmatch(rb'"(?:[^"\\]|\\.)*"',name) or re.fullmatch(rb'[^ (){}%*"\\]+',name)):continue
        try:return name.decode('ascii')
        except UnicodeDecodeError:continue
    raise RuntimeError('IMAP_SPECIAL_USE_UNAVAILABLE')

class HostingerEmailProvider:
    def __init__(self,settings=None):
        self.settings=settings or mail_settings();s=self.settings
        if (s.smtp_host,s.smtp_port,s.smtp_secure,s.imap_host,s.imap_port,s.imap_secure)!=('smtp.hostinger.com',465,True,'imap.hostinger.com',993,True):raise ValueError('Use the manually verified Hostinger TLS settings.')
        if not s.password.get_secret_value():raise ValueError('Mailbox secret is not configured.')
    def smtp(self):
        s=self.settings;client=smtplib.SMTP_SSL(s.smtp_host,s.smtp_port,timeout=20,context=ssl.create_default_context())
        try:client.login(s.username,s.password.get_secret_value())
        except Exception:client.close();raise SendFailed('SMTP_AUTH_OR_CONNECTION') from None
        return client
    def imap(self):
        s=self.settings;client=imaplib.IMAP4_SSL(s.imap_host,s.imap_port,ssl_context=ssl.create_default_context(),timeout=8)
        try:client.login(s.username,s.password.get_secret_value())
        except Exception:
            try:client.shutdown()
            except Exception:pass
            raise RuntimeError('IMAP_AUTH_OR_CONNECTION') from None
        return client
    def health_check(self):
        result={}
        for name,connect in [('smtp',self.smtp),('imap',self.imap)]:
            try:
                client=connect()
                try:
                    if name=='smtp':
                        code,_=client.noop()
                        if code!=250:raise RuntimeError('SMTP_HEALTH_FAILED')
                    else:
                        status,_=client.select('INBOX',readonly=True)
                        if status!='OK':raise RuntimeError('IMAP_INBOX_UNAVAILABLE')
                    result[name]='READY'
                finally:
                    try:client.quit() if name=='smtp' else client.logout()
                    except Exception:pass
            except Exception:result[name]='UNAVAILABLE'
        return result
    def send_message(self,message):
        import os
        from app.config.settings import get_settings
        if get_settings().app_env=='development' and os.environ.get('HEYSOW_LOCAL_PREVIEW')=='true':
            from email.utils import getaddresses
            recipients=getaddresses(message.get_all('To',[]))
            if (not self.settings.sending_enabled or self.settings.mode!='test' or not self.settings.test_recipient
                or len(recipients)!=1 or recipients[0][1].lower()!=self.settings.test_recipient.lower()):
                raise SendFailed('LOCAL_CONTROLLED_RECIPIENT_REQUIRED')
        try:client=self.smtp()
        except Exception:raise SendFailed('SMTP_CONNECTION_FAILED') from None
        try:
            refused=client.send_message(message,from_addr=self.settings.from_address,to_addrs=[message['To']])
            if refused:raise SendFailed('SMTP_RECIPIENT_REFUSED')
        except (smtplib.SMTPRecipientsRefused,smtplib.SMTPDataError,smtplib.SMTPSenderRefused):raise SendFailed('SMTP_REJECTED') from None
        except SendFailed:raise
        except Exception:raise SendUncertain('SMTP_RESULT_UNCERTAIN') from None
        finally:
            try:client.quit()
            except Exception:client.close()
        return str(message['Message-ID'])
    def sync_mailbox(self,client):return 'INBOX'
    def sent_mailbox(self,client):return special_use_folder(client,r'\Sent')
    def sync_messages(self,known_ids,cursor):
        client=self.imap();messages=[]
        try:
            folder=self.sync_mailbox(client)
            status,_=client.select(folder,readonly=True)
            if status!='OK':raise RuntimeError('IMAP_INBOX_UNAVAILABLE')
            validity=(client.response('UIDVALIDITY')[1] or [b''])[0].decode('ascii',errors='ignore')
            if self.settings.provider=='gmail':validity=hashlib.sha256((folder+'|'+validity).encode()).hexdigest()
            last=cursor.get('last_uid',0) if cursor.get('uidvalidity')==validity else 0
            since=(datetime.now(timezone.utc)-timedelta(days=self.settings.initial_days)).strftime('%d-%b-%Y')
            status,data=client.uid('search',None,'SINCE',since)
            if status!='OK':raise RuntimeError('IMAP_SEARCH_FAILED')
            uids=[int(x) for x in (data[0] or b'').split() if int(x)>last][:30];deadline=time.monotonic()+15
            for uid in uids:
                if time.monotonic()>deadline or len(messages)>=5:break
                status,parts=client.uid('fetch',str(uid),'(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID IN-REPLY-TO REFERENCES FROM TO SUBJECT DATE AUTO-SUBMITTED AUTHENTICATION-RESULTS CONTENT-TYPE ORIGINAL-MESSAGE-ID)])')
                last=uid
                if status!='OK':raise RuntimeError('IMAP_FETCH_FAILED')
                raw=b''.join(x[1] for x in parts if isinstance(x,tuple))
                if len(raw)>65536:continue
                headers=BytesParser(policy=policy.default).parsebytes(raw)
                refs=set(re.findall(r'<[^<>\s]+>',str(headers.get('In-Reply-To',''))+' '+str(headers.get('References',''))))
                is_dsn=headers.get_content_type()=='multipart/report' and headers.get_param('report-type')=='delivery-status'
                if not refs.intersection(known_ids) and not is_dsn:continue
                sizes=[int(x) for part in parts if isinstance(part,tuple) for x in re.findall(rb'RFC822.SIZE (\d+)',part[0])]
                if not sizes or max(sizes)>524288:continue
                status,parts=client.uid('fetch',str(uid),'(BODY.PEEK[])')
                if status!='OK':raise RuntimeError('IMAP_BODY_FAILED')
                content=b''.join(x[1] for x in parts if isinstance(x,tuple))
                if len(content)>524288:continue
                incoming=parse_incoming(content,known_ids,cursor.get('experiment_auto_refs',[]))
                if incoming:messages.append(incoming)
            return messages,{'uidvalidity':validity,'last_uid':last}
        finally:
            try:client.logout()
            except Exception:pass

class GmailEmailProvider(HostingerEmailProvider):
    """Gmail app-password TLS transport using the existing bounded sync/parser."""
    def sync_mailbox(self,client):return special_use_folder(client,r'\All')
    def __init__(self,settings=None):
        self.settings=settings or mail_settings();s=self.settings
        if (s.smtp_host,s.smtp_port,s.smtp_secure,s.imap_host,s.imap_port,s.imap_secure)!=('smtp.gmail.com',465,True,'imap.gmail.com',993,True):
            raise ValueError('Gmail requires the configured implicit TLS endpoints.')
        if not s.password.get_secret_value():raise ValueError('Mailbox secret is not configured.')
        if s.username.lower()!=s.from_address.lower():raise ValueError('Gmail sender must match the authenticated mailbox.')

def provider():
    settings=mail_settings()
    if settings.provider=='gmail':return GmailEmailProvider(settings)
    if settings.provider=='hostinger':return HostingerEmailProvider(settings)
    raise ValueError('Unsupported email provider')
