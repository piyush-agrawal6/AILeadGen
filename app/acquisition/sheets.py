"""Opt-in read-only Sheets OAuth, separate from normal Google sign-in scopes."""
import base64,csv,hashlib,io,json,re,secrets,uuid,os,time
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,quote,urlsplit
from pathlib import Path
from tempfile import NamedTemporaryFile
import httpx
from cryptography.fernet import Fernet,InvalidToken
from fastapi import HTTPException
from app.acquisition.config import settings
from app.config.settings import get_settings
from app.database.prospects import now
from app.acquisition import service
from app.acquisition.imports import headers,Spreadsheet,MAX_ROWS,MAX_UPLOAD_BYTES,ImportInvalid
from app.storage import artifact_storage

SCOPE='https://www.googleapis.com/auth/spreadsheets.readonly'
class SheetsUnavailable(RuntimeError):pass

def require_internal_connection():
    from app.platform.context import organization
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if organization()!=PLANEBYTE_ORGANIZATION_ID:
        raise HTTPException(409,'A workspace-specific Google Sheets connection is not configured.')

def cipher():
    secret=get_settings().api_signing_secret
    if len(secret)<32:raise SheetsUnavailable('Sheets requires the existing server signing secret.')
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(('leadengine:sheets:v1:'+secret).encode()).digest()))
def encrypt(value):return cipher().encrypt(json.dumps(value).encode()).decode()
def decrypt(value):
    try:return json.loads(cipher().decrypt(value.encode()))
    except (InvalidToken,ValueError):raise SheetsUnavailable('Google Sheets connection needs reconnecting.') from None

def start(c,actor):
    require_internal_connection()
    s=settings()
    if not s.google_id or not s.google_secret.get_secret_value():raise SheetsUnavailable('Existing Google OAuth client is not configured on the acquisition server.')
    if urlsplit(s.sheets_redirect_uri).scheme!='https' and get_settings().app_env=='production':raise SheetsUnavailable('Sheets callback requires HTTPS in production.')
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48);challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    c.execute('DELETE FROM acquisition_oauth_states WHERE expires_at<?',(now(),))
    c.execute('INSERT INTO acquisition_oauth_states(state_hash,actor,verifier_ciphertext,expires_at) VALUES(?,?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),actor,encrypt(verifier),(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()))
    params={'client_id':s.google_id,'redirect_uri':s.sheets_redirect_uri,'response_type':'code','scope':SCOPE,'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,'code_challenge_method':'S256','login_hint':actor}
    return {'authorization_url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(params),'scope':SCOPE,'redirect_uri':s.sheets_redirect_uri}

async def token_request(data):
    s=settings()
    if get_settings().app_env=='test' and os.getenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK')!='1':raise SheetsUnavailable('Provider requests are disabled in offline tests.')
    try:
        async with httpx.AsyncClient(timeout=20,trust_env=False,follow_redirects=False) as client:
            response=await client.post('https://oauth2.googleapis.com/token',data={**data,'client_id':s.google_id,'client_secret':s.google_secret.get_secret_value()})
        if len(response.content)>64_000:raise SheetsUnavailable('Google connection response exceeded its limit.')
        if response.status_code in (400,401):
            try:error=response.json().get('error')
            except (ValueError,AttributeError):error=None
            if error in ('invalid_grant','invalid_client','unauthorized_client'):
                raise HTTPException(409,'Google authorization expired or was revoked. Reconnect your account.')
        if response.status_code!=200:raise SheetsUnavailable('Google Sheets connection failed. Reconnect with read-only access.')
        return response.json()
    except (httpx.HTTPError,ValueError):raise SheetsUnavailable('Google Sheets connection unavailable. CSV/XLSX import remains available.') from None

async def connect(c,actor,state,code):
    require_internal_connection()
    hashed=hashlib.sha256(state.encode()).hexdigest();r=c.execute('SELECT * FROM acquisition_oauth_states WHERE state_hash=? AND actor=? AND expires_at>?',(hashed,actor,now())).fetchone()
    if not r:raise HTTPException(409,'Google connection state expired or does not belong to this account. Start again.')
    changed=c.execute('DELETE FROM acquisition_oauth_states WHERE state_hash=?',(hashed,)).rowcount;c.commit()
    if changed!=1:raise HTTPException(409,'Google connection state has already been used.')
    data=await token_request({'code':code,'code_verifier':decrypt(r['verifier_ciphertext']),'redirect_uri':settings().sheets_redirect_uri,'grant_type':'authorization_code'})
    if SCOPE not in data.get('scope','').split():raise SheetsUnavailable('Google did not grant read-only Sheets access.')
    old=c.execute('SELECT tokens_ciphertext FROM acquisition_google_connections WHERE actor=?',(actor,)).fetchone()
    if not data.get('refresh_token') and old:data['refresh_token']=decrypt(old[0]).get('refresh_token')
    if not data.get('access_token') or not data.get('refresh_token'):raise SheetsUnavailable('Reconnect and approve offline read-only Sheets access.')
    value={'access_token':data['access_token'],'refresh_token':data['refresh_token'],'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=int(data.get('expires_in',3600))-60)).isoformat()}
    c.execute('INSERT INTO acquisition_google_connections(actor,tokens_ciphertext,scopes,connected_at) VALUES(?,?,?,?) ON CONFLICT(actor) DO UPDATE SET tokens_ciphertext=excluded.tokens_ciphertext,scopes=excluded.scopes,connected_at=excluded.connected_at',(actor,encrypt(value),SCOPE,now()))
    return {'connected':True,'scope':SCOPE}

async def access_token(c,actor):
    require_internal_connection()
    r=c.execute('SELECT tokens_ciphertext FROM acquisition_google_connections WHERE actor=?',(actor,)).fetchone()
    if not r:raise SheetsUnavailable('Connect Google Sheets with read-only access first.')
    value=decrypt(r[0])
    if value['expires_at']<=now():
        result=await token_request({'grant_type':'refresh_token','refresh_token':value['refresh_token']})
        if not result.get('access_token'):raise SheetsUnavailable('Google connection expired; reconnect.')
        value.update(access_token=result['access_token'],expires_at=(datetime.now(timezone.utc)+timedelta(seconds=int(result.get('expires_in',3600))-60)).isoformat());c.execute('UPDATE acquisition_google_connections SET tokens_ciphertext=? WHERE actor=?',(encrypt(value),actor))
    return value['access_token']

def spreadsheet_id(value):
    match=re.fullmatch(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]{10,200})(?:/[^\s]*)?',value)
    identifier=match[1] if match else value
    if not re.fullmatch(r'[a-zA-Z0-9_-]{10,200}',identifier):raise ImportInvalid('Paste a Google Sheets URL or spreadsheet ID.')
    return identifier

async def get(c,actor,path,params):
    if get_settings().app_env=='test' and os.getenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK')!='1':raise SheetsUnavailable('Provider requests are disabled in offline tests.')
    token=await access_token(c,actor)
    return await read_with_token(token,path,params)

async def read_with_token(token,path,params):
    """Shared bounded provider transport; callers supply verified connection authority."""
    if get_settings().app_env=='test' and os.getenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK')!='1':raise SheetsUnavailable('Provider requests are disabled in offline tests.')
    try:
        async with httpx.AsyncClient(timeout=25,trust_env=False,follow_redirects=False) as client:
            async with client.stream('GET','https://sheets.googleapis.com/v4/spreadsheets/'+path,params=params,headers={'Authorization':'Bearer '+token}) as response:
                if response.status_code!=200:raise SheetsUnavailable('Google Sheet is unavailable to the connected account (HTTP '+str(response.status_code)+').')
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>2_000_000:raise SheetsUnavailable('Sheet range exceeds the bounded read limit; use a smaller range or CSV.')
        return json.loads(raw)
    except (httpx.HTTPError,ValueError):raise SheetsUnavailable('Google Sheets is unavailable. CSV/XLSX upload remains available.') from None

async def metadata(c,actor,value,reader=None):
    sid=spreadsheet_id(value);data=await (reader or get)(c,actor,sid,{'fields':'spreadsheetId,properties(title),sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))'})
    tabs=[r['properties'] for r in data.get('sheets',[])][:50]
    return {'spreadsheet_id':sid,'title':data.get('properties',{}).get('title','Google Sheet'),'tabs':tabs}
async def values(c,actor,sid,tab,start,end,reader=None):
    area="'"+tab.replace("'","''")+"'!A"+str(start)+':AX'+str(end)
    result=await (reader or get)(c,actor,sid+'/values/'+quote(area,safe=''),{'valueRenderOption':'UNFORMATTED_VALUE','dateTimeRenderOption':'FORMATTED_STRING'})
    return result.get('values',[])

async def stage(c,actor,value,tab,key,*,reader=None,connection=None):
    meta=await metadata(c,actor,value,**({'reader':reader} if reader else {}));selected=next((x for x in meta['tabs'] if x['title']==tab),None)
    if not selected:raise ImportInvalid('Select a tab from the connected spreadsheet.')
    grid=selected.get('gridProperties',{})
    if grid.get('columnCount',0)>50:raise ImportInvalid('Import supports at most 50 sheet columns; remove unused columns or use CSV.')
    if grid.get('rowCount',0)>MAX_ROWS+1:raise ImportInvalid('This tab exceeds 10,000 grid rows. Trim unused rows or upload a bounded CSV/XLSX export.')
    rows=await values(c,actor,meta['spreadsheet_id'],tab,1,6,**({'reader':reader} if reader else {}))
    if not rows:raise ImportInvalid('Selected tab is empty.')
    columns=headers(rows[0]);manifest={'sheets':[x['title'] for x in meta['tabs']],'sheet':tab,'headers':columns,'sample':rows[1:6],'row_count':max(0,grid.get('rowCount',1)-1),'row_count_is_estimate':True,'file_format':'GOOGLE_SHEETS'}
    origin={'spreadsheet_id':meta['spreadsheet_id'],'spreadsheet_url':'https://docs.google.com/spreadsheets/d/'+meta['spreadsheet_id'],'spreadsheet_title':meta['title'],'sheet':tab,'sheet_id':selected['sheetId'],'grid_rows':grid.get('rowCount',1),'filename':meta['title'][:150]+'.csv'}
    if connection:origin.update(workspace_connection_id=connection['id'],workspace_connection_revision=connection['revision'])
    r=service.create_job(c,'GOOGLE_SHEETS',actor,key,{},origin,status='MAPPING_REVIEW');c.execute('UPDATE acquisition_jobs SET manifest_json=? WHERE id=?',(service.encoded(manifest),r['id']));return service.detail(c,r['id'])

async def snapshot(c,r):
    expected_lease=r.get('lease_owner');r=service.job(c,r['id']);origin=json.loads(r['origin_json']);reader=None
    deadline=time.monotonic()+min(120,int(json.loads(r['configuration_json']).get('budgets',{}).get('max_runtime_seconds',120)))
    def check():
        current=service.job(c,r['id'])
        if current['status'] not in ('MAPPING_REVIEW','QUEUED','RUNNING') or current['lease_owner']!=expected_lease:raise HTTPException(409,'Spreadsheet import was stopped or its worker ownership changed.')
        if time.monotonic()>=deadline:raise SheetsUnavailable('Spreadsheet snapshot exceeded its bounded read time. Retry explicitly or use a smaller tab.')
    check()
    if origin.get('workspace_connection_id'):
        from app.integrations.google_sheets import reader_for
        reader=reader_for(origin['workspace_connection_id'],origin['workspace_connection_revision'],importing=True)
    else:require_internal_connection()
    origin=json.loads(r['origin_json']);manifest=json.loads(r['manifest_json']);buffer=io.StringIO(newline='');writer=csv.writer(buffer);nonempty=0
    for start_row in range(1,origin['grid_rows']+1,250):
        check()
        rows=await values(c,r['owner'],origin['spreadsheet_id'],origin['sheet'],start_row,min(origin['grid_rows'],start_row+249),**({'reader':reader} if reader else {}))
        check()
        if start_row==1:
            if not rows or headers(rows[0])!=manifest['headers']:raise ImportInvalid('Sheet headers changed after mapping review. Create a new import and review mapping again.')
        if start_row+249<origin['grid_rows']:rows=rows+[[] for _ in range(max(0,250-len(rows)))]
        for row in rows:
            if any(len(str(v or ''))>4096 for v in row):raise ImportInvalid('Sheet cell exceeds 4,096 characters.')
            writer.writerow(row)
        if buffer.tell()>MAX_UPLOAD_BYTES:raise ImportInvalid('Sheet snapshot exceeds 1 MB; import a smaller tab or bounded file.')
    raw=buffer.getvalue().encode('utf-8');book=Spreadsheet(raw,origin['filename']);current=book.inspect();current.update(sheets=manifest['sheets'],sheet=manifest['sheet'],file_format='GOOGLE_SHEETS',snapshot_at=now(),row_count_is_estimate=False)
    check();key='audits/acquisition/'+r['id']+'/sheet-snapshot-'+hashlib.sha256(raw).hexdigest()+'.csv'
    with NamedTemporaryFile(suffix='.csv') as f:f.write(raw);f.flush();artifact_storage().put(key,Path(f.name),'text/csv')
    check()
    changed=c.execute("UPDATE acquisition_jobs SET upload_key=?,manifest_json=? WHERE id=? AND organization_id=? AND status IN ('MAPPING_REVIEW','QUEUED','RUNNING') AND COALESCE(lease_owner,'')=?",(key,service.encoded(current),r['id'],r['organization_id'],expected_lease or '')).rowcount
    if not changed:raise HTTPException(409,'Spreadsheet import ownership changed before saving its snapshot.')
    return key
