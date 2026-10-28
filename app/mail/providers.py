"""Verified Hostinger SMTP/IMAP only; no discovery, POP3 or credential logging."""
import imaplib,smtplib,ssl,re,time
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
    def sync_messages(self,known_ids,cursor):
        client=self.imap();messages=[]
        try:
            status,_=client.select('INBOX',readonly=True)
            if status!='OK':raise RuntimeError('IMAP_INBOX_UNAVAILABLE')
            validity=(client.response('UIDVALIDITY')[1] or [b''])[0].decode('ascii',errors='ignore')
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
                parsed=BytesParser(policy=policy.default).parsebytes(content)
                if is_dsn:
                    from app.mail.bounces import parse_dsn
                    dsn=parse_dsn(parsed)
                    if dsn:messages.append({**dsn,'message_id':str(parsed.get('Message-ID','')),'from':str(parsed.get('From','')),'to':str(parsed.get('To','')),'date':str(parsed.get('Date','')),'authentication':str(parsed.get('Authentication-Results',''))})
                    continue
                if str(parsed.get('Auto-Submitted','no')).lower()!='no':continue
                body=parsed.get_body(preferencelist=('plain','html')) if parsed.is_multipart() else parsed
                text=''
                if body:
                    try:text=body.get_content()
                    except Exception:text='Message text unavailable.'
                    if body.get_content_type()=='text/html':
                        soup=BeautifulSoup(text,'html.parser')
                        for node in soup(['script','style','iframe','object']):node.decompose()
                        text=soup.get_text(' ',strip=True)
                messages.append({'message_id':str(parsed.get('Message-ID','')),'from':str(parsed.get('From','')),'to':str(parsed.get('To','')),'subject':str(parsed.get('Subject',''))[:300],'references':list(refs),'in_reply_to':str(parsed.get('In-Reply-To','')),'body_text':str(text)[:20000],'date':str(parsed.get('Date','')),'authentication':str(parsed.get('Authentication-Results',''))})
            return messages,{'uidvalidity':validity,'last_uid':last}
        finally:
            try:client.logout()
            except Exception:pass

class GmailEmailProvider:
    """Optional future OAuth adapter; never accepts mailbox passwords."""
    def health_check(self):return {'status':'NOT_CONFIGURED','reason':'Optional Gmail OAuth is not enabled.'}
    def send_message(self,message):raise SendFailed('GMAIL_NOT_CONFIGURED')
    def sync_messages(self,known_ids,cursor):return [],cursor

def provider():
    settings=mail_settings()
    if settings.provider!='hostinger':raise ValueError('Only the configured Hostinger provider is enabled.')
    return HostingerEmailProvider(settings)
