"""Reviewed list snapshots -> fixed Sheets range. Never append or discover leads."""
import asyncio,hashlib,json,secrets,uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
import httpx
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.integrations import service
from app.acquisition.sheets import spreadsheet_id
from app.database.prospects import now
from app.platform.context import current,organization,job_scope
from app.database.connection import db_session
from app.config.settings import get_settings

class Export(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    list_id:uuid.UUID
    spreadsheet:str=Field(min_length=10,max_length=500)
    sheet:str=Field(min_length=1,max_length=100)
    start_row:int=Field(1,ge=1,le=100000)
    request_id:uuid.UUID
    @field_validator('sheet')
    @classmethod
    def title(cls,value):
        if any(ord(char)<32 for char in value):raise ValueError('Use a valid tab title.')
        return value

def connection(c,key,revision=None):
    service.manager(c);row=service.owned(c,key)
    if row['status']!='CONNECTED' or row['provider']!=service.PROVIDER or service.WRITE_SCOPE not in json.loads(row['scopes_json']):
        raise HTTPException(409,'Explicitly connect Google Sheets with export permission before preparing an export.')
    if revision is not None and row['revision']!=revision:raise HTTPException(409,'The connection changed after review. Prepare a fresh export.')
    return row

def table_for(key):
    return 'radar_sheet_exports' if uuid.UUID(key).version==5 else 'organization_sheet_exports'

def owned(c,key):
    service.manager(c);table=table_for(key)
    if table=='radar_sheet_exports':
        from app.integrations.radar_sheets import admin
        admin(c)
    row=c.execute(f'SELECT * FROM {table} WHERE id=? AND organization_id=?',(key,organization())).fetchone()
    if not row:raise HTTPException(404,'Spreadsheet export not found.')
    return dict(row)

def view(row):
    if 'selection_json' in row:
        from app.integrations.radar_sheets import describe
        return describe(row)
    rows=json.loads(row['rows_json'])
    return {name:row[name] for name in ('id','connection_id','list_id','spreadsheet_id','sheet_title','target_range','status','attempts','last_error_code','created_at','expires_at','completed_at')}|{'row_count':len(rows)-1,'columns':rows[0],'preview':rows[1:6],'review_digest':row['fingerprint']}

def listing(c,key):
    service.manager(c);service.owned(c,key)
    return {'items':[view(dict(row)) for row in c.execute('SELECT * FROM organization_sheet_exports WHERE organization_id=? AND connection_id=? ORDER BY created_at DESC LIMIT 25',(organization(),key)).fetchall()]}

def stage(c,key,body):
    org=service.lock(c);row=connection(c,key);sid=spreadsheet_id(body.spreadsheet)
    from app.sales.collections import get,detail
    parent=get(c,str(body.list_id))
    if parent['archived_at']:raise HTTPException(409,'Choose an active company list.')
    old=c.execute('SELECT * FROM organization_sheet_exports WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
    request=[key,str(body.list_id),sid,body.sheet,body.start_row]
    if old:
        if old['created_by']!=current().actor or [old['connection_id'],old['list_id'],old['spreadsheet_id'],old['sheet_title'],int(old['target_range'].split('!A')[-1].split(':')[0])]!=request:
            raise HTTPException(409,'Export request ID belongs to different content.')
        return view(dict(old))
    cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    if c.execute('SELECT COUNT(*) FROM organization_sheet_exports WHERE organization_id=? AND created_at>?',(org,cutoff)).fetchone()[0]>=20:raise HTTPException(429,'Review existing exports before preparing more.')
    data=detail(c,str(body.list_id),1,500)
    if data['company_count']>500:raise HTTPException(422,'Choose a list with at most 500 companies for this bounded export.')
    if not data['companies']:raise HTTPException(422,'Add companies to the list before exporting.')
    if len(data['companies'])!=data['company_count']:raise HTTPException(409,'Some selected company records are unavailable. Review the list before exporting.')
    ids=[company['id'] for company in data['companies']];marks=','.join('?' for _ in ids)
    evidence={row['id']:dict(row) for row in c.execute('SELECT b.id,b.public_email,b.source_overture,b.source_osm,r.run_configuration_json FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE r.organization_id=? AND b.id IN ('+marks+')',[org,*ids]).fetchall()}
    if len(evidence)!=len(ids):raise HTTPException(409,'Some selected company records are unavailable. Review the list before exporting.')
    sources={bid:set() for bid in ids}
    for item in c.execute('SELECT DISTINCT business_id,source_type FROM lead_source_evidence WHERE organization_id=? AND business_id IN ('+marks+') LIMIT 5000',[org,*ids]).fetchall():sources[item['business_id']].add(item['source_type'])
    columns=['Company','Website','Business email','Country','City','Lead status','Source','Company ID'];rows=[columns]
    for company in data['companies']:
        record=evidence[company['id']];labels=sources[company['id']]
        if record['source_overture']:labels.add('OVERTURE')
        if record['source_osm']:labels.add('OSM')
        source=json.loads(record['run_configuration_json'] or '{}').get('source_type')
        if source in ('OVERTURE','FIRECRAWL','CSV','XLSX','GOOGLE_SHEETS'):labels.add(source)
        values=[company['name'],company['website'],record['public_email'],company['country'],company['city'],company['lead_status'],', '.join(sorted(labels)),str(company['id'])]
        rows.append([''.join(char for char in str(value or '') if ord(char)>=32)[:2000] for value in values])
    target="'"+body.sheet.replace("'","''")+"'!A"+str(body.start_row)+':H'+str(body.start_row+len(rows)-1)
    encoded=json.dumps(rows,ensure_ascii=False,separators=(',',':'))
    if len(encoded.encode())>1_000_000:raise HTTPException(422,'Export exceeds its snapshot size budget. Use a smaller list.')
    digest=hashlib.sha256(json.dumps([sid,target,rows],ensure_ascii=False).encode()).hexdigest();stamp=now();export_id=str(uuid.uuid4())
    c.execute('INSERT INTO organization_sheet_exports(id,organization_id,connection_id,connection_revision,created_by,list_id,request_id,fingerprint,spreadsheet_id,sheet_title,target_range,rows_json,created_at,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (export_id,org,key,row['revision'],current().actor,str(body.list_id),str(body.request_id),digest,sid,body.sheet,target,encoded,stamp,(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat(),stamp))
    service.audit(c,key,'SHEETS_EXPORT_STAGED');return view(owned(c,export_id))

def approve(c,key,digest,confirmation):
    service.lock(c)
    row=owned(c,key);connection(c,row['connection_id'],row['connection_revision'])
    if confirmation!='OVERWRITE_REVIEWED_RANGE' or not secrets.compare_digest(digest,row['fingerprint']):raise HTTPException(409,'Review the exact destination and snapshot before exporting.')
    if row['expires_at']<now():raise HTTPException(409,'Export review expired. Prepare a fresh snapshot.')
    if row['status']=='COMPLETED':return view(row)
    if row['status'] not in ('DRAFT','QUEUED'):raise HTTPException(409,'Review the failed or uncertain outcome before explicitly retrying.')
    if 'selection_json' in row:
        from app.integrations.radar_sheets import verified_rows
        verified_rows(c,row)
    c.execute(f"UPDATE {table_for(key)} SET status='QUEUED',updated_at=? WHERE id=? AND organization_id=? AND status='DRAFT'",(now(),key,organization()))
    service.audit(c,row['connection_id'],'SHEETS_EXPORT_APPROVED');return view(owned(c,key))

def retry(c,key,digest,confirmation):
    service.lock(c)
    row=owned(c,key);connection(c,row['connection_id'],row['connection_revision'])
    if row['expires_at']<now() or row['attempts']>=3:raise HTTPException(409,'Export expired or has exhausted its three attempts.')
    if row['status']=='RUNNING' and row['lease_until'] and row['lease_until']>=now():raise HTTPException(409,'The export is still running.')
    if row['status'] not in ('FAILED','UNCERTAIN','RUNNING'):raise HTTPException(409,'Only a failed or uncertain export can be retried.')
    if confirmation!='OVERWRITE_REVIEWED_RANGE' or not secrets.compare_digest(digest,row['fingerprint']):raise HTTPException(409,'Confirm overwriting the same reviewed range before retrying.')
    if 'selection_json' in row:
        from app.integrations.radar_sheets import verified_rows
        verified_rows(c,row)
    c.execute(f"UPDATE {table_for(key)} SET status='QUEUED',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=? AND organization_id=?",(now(),key,organization()))
    service.audit(c,row['connection_id'],'SHEETS_EXPORT_RETRY_APPROVED');return view(owned(c,key))

async def write(token,sid,target,rows,transport=None):
    if get_settings().app_env=='test' and transport is None:raise HTTPException(503,'Provider writes are disabled in offline tests.')
    # Fixed provider host/path; RAW prevents imported text from becoming formulas.
    async with asyncio.timeout(30):
        async with httpx.AsyncClient(timeout=httpx.Timeout(25,connect=5),follow_redirects=False,trust_env=False,transport=transport) as client:
            async with client.stream('PUT','https://sheets.googleapis.com/v4/spreadsheets/'+quote(sid,safe='')+'/values/'+quote(target,safe=''),params={'valueInputOption':'RAW','includeValuesInResponse':'false'},headers={'Authorization':'Bearer '+token},json={'range':target,'majorDimension':'ROWS','values':rows}) as response:
                status=response.status_code
                if not 200<=status<300:return status,False
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>32000:return status,False
                try:result=json.loads(raw)
                except (ValueError,UnicodeError):return status,False
                return status,isinstance(result,dict) and result.get('updatedCells')==sum(len(row) for row in rows)

async def execute(key,db_path=None,transport=None):
    service.require_enabled()
    with db_session(db_path) as c:
        table=table_for(key);radar=table=='radar_sheet_exports'
        with job_scope(c,'radar_sheet_export' if radar else 'sheet_export',key):
            row=owned(c,key);connection(c,row['connection_id'],row['connection_revision'])
            if row['expires_at']<now():
                if radar:c.execute("UPDATE radar_sheet_exports SET status='FAILED',last_error_code='REVIEW_EXPIRED',updated_at=? WHERE id=? AND organization_id=? AND status='QUEUED'",(now(),key,organization()))
                return
            from app.workflows.service import lock
            lock(c)
            if c.execute(f"SELECT COUNT(*) FROM {table} WHERE status='RUNNING' AND lease_until>?",(now(),)).fetchone()[0]>=2:
                if radar:c.execute("UPDATE radar_sheet_exports SET status='FAILED',last_error_code='WORKER_CAPACITY',updated_at=? WHERE id=? AND organization_id=? AND status='QUEUED'",(now(),key,organization()))
                return
            token=secrets.token_hex(16);expiry=(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()
            changed=c.execute(f"UPDATE {table} SET status='RUNNING',attempts=attempts+1,lease_owner=?,lease_until=?,updated_at=? WHERE id=? AND organization_id=? AND status='QUEUED' AND attempts<3",(token,expiry,now(),key,organization())).rowcount
            if not changed:return
            c.commit();state='FAILED';error='CONNECTION_UNAVAILABLE';started=False
            try:
                access,revision=await service.access_token(c,row['connection_id'])
                connection(c,row['connection_id'],row['connection_revision'])
                renewed=(datetime.now(timezone.utc)+timedelta(seconds=45)).isoformat()
                if radar:
                    from app.integrations.radar_sheets import verified_rows
                    rows=verified_rows(c,row)
                else:rows=json.loads(row['rows_json'])
                if not c.execute(f"UPDATE {table} SET lease_until=? WHERE id=? AND organization_id=? AND lease_owner=? AND status='RUNNING'",(renewed,key,organization(),token)).rowcount:return
                c.commit()
                started=True;status,verified=await write(access,row['spreadsheet_id'],row['target_range'],rows,transport)
                state='COMPLETED' if verified else 'UNCERTAIN' if 200<=status<300 else 'FAILED';error=None if verified else 'SHEETS_WRITE_UNVERIFIED' if 200<=status<300 else 'SHEETS_HTTP_'+str(status)
            except HTTPException:state='UNCERTAIN' if started else 'FAILED';error='CONNECTION_CHANGED' if started else 'CONNECTION_UNAVAILABLE'
            except (httpx.HTTPError,TimeoutError):state='UNCERTAIN';error='PROVIDER_OUTCOME_UNKNOWN'
            except Exception:state='UNCERTAIN' if started else 'FAILED';error='EXPORT_UNAVAILABLE'
            c.execute(f'UPDATE {table} SET status=?,last_error_code=?,updated_at=?,completed_at=?,lease_owner=NULL,lease_until=NULL WHERE id=? AND organization_id=? AND lease_owner=?',(state,error,now(),now() if state=='COMPLETED' else None,key,organization(),token))
            service.audit(c,row['connection_id'],'SHEETS_EXPORT_'+state)

def cancel(c,key):
    service.lock(c)
    row=owned(c,key)
    if row['status']=='RUNNING':raise HTTPException(409,'An in-flight provider write cannot be retracted. Wait for its recorded outcome.')
    if row['status']=='COMPLETED':raise HTTPException(409,'A completed export cannot be retracted.')
    if not c.execute(f"UPDATE {table_for(key)} SET status='CANCELLED',updated_at=? WHERE id=? AND organization_id=? AND status NOT IN ('RUNNING','COMPLETED')",(now(),key,organization())).rowcount:raise HTTPException(409,'Export state changed; refresh history.')
    service.audit(c,row['connection_id'],'SHEETS_EXPORT_CANCELLED');return view(owned(c,key))

_tasks=set()
async def launch(key):
    service.require_enabled()
    if get_settings().app_env=='production':
        from app.api.services.cloud_executor import run_job
        await asyncio.to_thread(run_job,None,sheet_export_id=key);return
    if len(_tasks)>=2:raise HTTPException(429,'Two exports are running. Retry the queued export shortly.')
    task=asyncio.create_task(execute(key));_tasks.add(task)
    def done(completed):
        _tasks.discard(completed)
        if not completed.cancelled():completed.exception()
    task.add_done_callback(done)

async def shutdown():
    pending=list(_tasks)
    for task in pending:task.cancel()
    if pending:await asyncio.gather(*pending,return_exceptions=True)
    _tasks.clear()
