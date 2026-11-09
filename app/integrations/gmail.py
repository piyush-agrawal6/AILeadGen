"""Gmail adapter over the shared PKCE/envelope/revision/refresh lifecycle."""
import asyncio,json,re,os
from datetime import datetime,timezone,timedelta
import httpx
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import current,organization
from app.integrations import service
from app.acquisition import sheets

SCOPE='openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly'

class GmailRejected(Exception):
    def __init__(self,status):self.status=status

async def request_json(method,url,token,*,params=None,payload=None):
    """Fixed provider destinations, bounded JSON and no arbitrary provider errors."""
    if get_settings().app_env=='test' and os.getenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK')!='1':raise sheets.SheetsUnavailable('Provider requests are disabled in offline tests.')
    try:
        async with httpx.AsyncClient(timeout=10,follow_redirects=False,trust_env=False) as client:
            async with client.stream(method,url,headers={'Authorization':'Bearer '+token},params=params,json=payload) as response:
                if response.status_code>=300:raise GmailRejected(response.status_code)
                data=bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data)>1_000_000:raise sheets.SheetsUnavailable('Provider response exceeds the connection limit.')
                result=json.loads(data)
                if not isinstance(result,dict):raise ValueError()
                return result
    except (httpx.HTTPError,ValueError):raise sheets.SheetsUnavailable('Gmail is temporarily unavailable.') from None

async def api(method,path,token,*,params=None,payload=None):
    if not re.fullmatch(r'(?:profile|history|messages(?:/(?:send|[A-Za-z0-9_-]{1,100}))?)',path):raise HTTPException(422,'Invalid Gmail operation.')
    return await request_json(method,'https://gmail.googleapis.com/gmail/v1/users/me/'+path,token,params=params,payload=payload)

async def exchange(payload):
    result=await sheets.token_request(payload)
    if payload.get('grant_type')=='authorization_code':
        # Validate the granted scope before reading any mailbox/profile data.
        service.token_value(result,expected_scope=SCOPE,spec=spec())
        try:
            identity=await request_json('GET','https://openidconnect.googleapis.com/v1/userinfo',result['access_token'])
            profile=await api('GET','profile',result['access_token'])
        except GmailRejected:raise HTTPException(409,'Gmail account verification was rejected. Reconnect with your own Google account.') from None
        email=identity.get('email');subject=identity.get('sub')
        if (identity.get('email_verified') is not True or not isinstance(email,str) or email.lower()!=current().actor
            or not isinstance(subject,str) or not 1<=len(subject)<=255 or profile.get('emailAddress','').lower()!=email.lower()):
            raise HTTPException(403,'Connect the verified Google account belonging to your signed-in identity.')
        result={**result,'identity':{'email_address':email.lower(),'google_subject':subject}}
    return result

def connected(c,row,value):
    from app.mail.service import address
    identity=value.get('identity')
    if not isinstance(identity,dict) or identity.get('email_address')!=current().actor:raise HTTPException(403,'Mailbox identity does not match the signed account.')
    email=address(identity['email_address']);subject=identity.get('google_subject')
    admission=c.execute('SELECT google_subject FROM account_admissions WHERE user_id=?',(current().actor,)).fetchone()
    if admission and admission['google_subject']!=subject:raise HTTPException(403,'Mailbox identity does not match the admitted Google account.')
    if row['google_subject'] and row['google_subject']!=subject:raise HTTPException(409,'Reconnect the original Google mailbox identity.')
    account='gmail-'+row['id'];stamp=now()
    existing=c.execute('SELECT organization_id,user_id,email_address FROM email_accounts WHERE id=?',(account,)).fetchone()
    if existing and (existing['organization_id']!=organization() or existing['user_id']!=current().actor or existing['email_address']!=email):raise HTTPException(409,'Mailbox ownership is inconsistent.')
    c.execute("INSERT INTO email_accounts(id,user_id,provider,email_address,display_name,status,created_at,updated_at,organization_id) VALUES(?,?,'gmail_oauth',?,?,'CONNECTED',?,?,?) ON CONFLICT(id) DO UPDATE SET status='CONNECTED',updated_at=excluded.updated_at WHERE email_accounts.organization_id=excluded.organization_id AND email_accounts.user_id=excluded.user_id",(account,current().actor,email,email,stamp,stamp,organization()))
    c.execute('UPDATE customer_gmail_connections SET account_id=?,email_address=?,google_subject=? WHERE id=? AND organization_id=?',(account,email,subject,row['id'],organization()))
    # Reconnection changes authority and invalidates any prior live approval.
    c.execute('UPDATE customer_mail_policies SET sending_approved=0,revision=revision+1,approved_by=NULL,approved_at=NULL,updated_at=? WHERE organization_id=?',(stamp,organization()))
    c.execute("UPDATE customer_gmail_sync SET cursor_json='{}',attempts=0,next_attempt_at=NULL,lease_id=NULL,lease_until=NULL,last_error_code=NULL WHERE connection_id=? AND organization_id=?",(row['id'],organization()))

def spec():
    return service.ProviderSpec(provider='GMAIL',table='customer_gmail_connections',states='customer_gmail_oauth_states',scope=SCOPE,
        redirect_uri=get_settings().heysow_customer_gmail_redirect_uri,user_owned=True,exchange=exchange,connected=connected)

def require_enabled():service.require_spec(spec())

def view(row):
    return service.view(row)|{name:row[name] for name in ('account_id','email_address','owner_user_id')}

def listing(c):
    require_enabled();org=service.reader(c)
    rows=c.execute('SELECT * FROM customer_gmail_connections WHERE organization_id=?',(org,)).fetchall()
    from app.api.organization import membership_role
    return {'items':[view(dict(row)) for row in rows],
        'can_connect':membership_role(c,current().actor,org) in ('OWNER','ADMIN') and (not rows or rows[0]['owner_user_id']==current().actor),
        'configured':service.configured() and bool(get_settings().heysow_customer_gmail_redirect_uri),'scope':SCOPE}

def disconnect(c,key):
    row=service.owned(c,key,spec=spec());result=service.disconnect(c,key,spec=spec())
    c.execute("UPDATE email_accounts SET status='DISCONNECTED',updated_at=? WHERE id=? AND organization_id=?",(now(),row['account_id'],organization()))
    c.execute('UPDATE customer_mail_policies SET sending_approved=0,revision=revision+1,approved_by=NULL,approved_at=NULL,updated_at=? WHERE organization_id=?',(now(),organization()))
    return result

async def health(c,key):
    service.manager(c);row=service.owned(c,key,spec=spec());token,revision=await service.access_token(c,key,spec=spec())
    try:
        profile=await api('GET','profile',token)
        if profile.get('emailAddress','').lower()!=row['email_address']:raise HTTPException(409,'Mailbox identity changed. Reconnect before sending.')
    except GmailRejected as exc:
        service.provider_error(c,row,'GMAIL_AUTH_REJECTED',reauth=exc.status in (401,403),spec=spec())
        raise HTTPException(503,'Gmail connection health could not be verified.') from None
    except sheets.SheetsUnavailable:
        service.provider_error(c,row,'GMAIL_UNAVAILABLE',spec=spec())
        raise HTTPException(503,'Gmail is temporarily unavailable.') from None
    service.manager(c);latest=service.owned(c,key,spec=spec())
    if latest['revision']!=revision or latest['status']!='CONNECTED':raise HTTPException(409,'Connection changed during health check.')
    c.execute('UPDATE customer_gmail_connections SET last_success_at=?,last_error_code=NULL WHERE id=? AND organization_id=? AND revision=?',(now(),key,organization(),revision))
    c.execute("UPDATE email_accounts SET smtp_health='READY',imap_health='READY',health_checked_at=? WHERE id=? AND organization_id=?",(now(),row['account_id'],organization()))
    return {'sending':'READY','inbox':'READY','email_address':row['email_address'],'checked_at':now()}

async def sync_messages(token,known,cursor):
    """One bounded provider page, advancing its cursor only after durable ingestion."""
    from app.mail.providers import parse_incoming
    profile=await api('GET','profile',token)
    if profile.get('emailAddress','').lower()!=current().actor:raise HTTPException(409,'Gmail synchronization identity does not match the mailbox owner.')
    params={'maxResults':25};history=cursor.get('history_id')
    initial=not history
    snapshot=cursor.get('snapshot_history_id') or profile.get('historyId')
    if not isinstance(snapshot,str) or not re.fullmatch(r'[0-9]{1,30}',snapshot):raise HTTPException(503,'Gmail history identity is unavailable.')
    if cursor.get('page_token'):params['pageToken']=cursor['page_token']
    if cursor.get('pending_ids'):
        ids=cursor['pending_ids'];data={'nextPageToken':cursor.get('page_token')}
    elif initial:
        params['q']='newer_than:30d';data=await api('GET','messages',token,params=params)
        ids=[entry.get('id') for entry in data.get('messages',[])[:25]]
    else:
        params.update(startHistoryId=history,historyTypes='messageAdded')
        try:data=await api('GET','history',token,params=params)
        except GmailRejected as exc:
            if exc.status==404:raise HTTPException(409,'Gmail history expired. Review and restart the bounded inbox sync.') from None
            raise
        records=data.get('history',[])
        if not isinstance(records,list) or len(records)>25:raise HTTPException(503,'Gmail history exceeds this bounded page.')
        ids=list(dict.fromkeys(entry.get('message',{}).get('id') for item in records for entry in item.get('messagesAdded',[])))
    if not isinstance(ids,list) or len(ids)>1000:raise HTTPException(503,'Gmail message page exceeds the bounded sync limit.')
    pending=ids[25:];ids=ids[:25]
    semaphore=asyncio.Semaphore(3)
    async def read(key):
        import base64
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',key):return None
        async with semaphore:
            raw=await api('GET','messages/'+key,token,params={'format':'raw'})
            encoded=raw.get('raw','')
            if not isinstance(encoded,str) or len(encoded)>700_000:return None
            try:content=base64.b64decode(encoded+'='*(-len(encoded)%4),altchars=b'-_',validate=True)
            except ValueError:return None
            return parse_incoming(content,known)
    messages=await asyncio.gather(*(read(key) for key in ids))
    next_page=data.get('nextPageToken')
    if next_page and (not isinstance(next_page,str) or len(next_page)>2000):raise HTTPException(503,'Gmail pagination is unavailable.')
    more=bool(next_page or pending)
    updated={'page_token':next_page,'history_id':history if more else snapshot,'pending_ids':pending}
    if more:updated['snapshot_history_id']=snapshot
    return [message for message in messages if message],updated
