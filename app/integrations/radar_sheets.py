"""Reviewed Radar snapshots retain selection and digest, not a second copy of source text."""
import hashlib,json,uuid
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.integrations import service,sheet_exports
from app.intent_radar import exports
from app.intent_radar.permissions import context
from app.database.prospects import now
from app.acquisition.sheets import spreadsheet_id
from app.config.settings import get_settings
from dataclasses import replace
from urllib.parse import quote,urlsplit,urlunsplit

def oauth_spec():
    s=get_settings()
    callback='/intent-radar/integrations/sheets/callback'
    if s.app_env!='production' and not s.radar_google_sheets_redirect_uri:
        from app.acquisition.config import settings
        origin=urlsplit(settings().sheets_redirect_uri)
        return replace(service.SHEETS,redirect_uri=urlunsplit((origin.scheme,origin.netloc,callback,'','')))
    if s.radar_google_sheets_redirect_uri!='https://app.planebyte.com'+callback:raise HTTPException(503,'The Radar Google Sheets callback requires server setup.')
    return replace(service.SHEETS,redirect_uri=s.radar_google_sheets_redirect_uri)

class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    selection:exports.Selection
    spreadsheet:str=Field(min_length=10,max_length=500)
    sheet:str=Field(min_length=1,max_length=100,pattern=r'^[^\x00-\x1f]+$')
    start_row:int=Field(1,ge=1,le=100000)
    request_id:uuid.UUID

def admin(c):
    ctx=context(c,True,True);service.manager(c)
    s=get_settings()
    if s.app_env=='production' and ctx.organization_id not in {v.strip() for v in s.radar_sheets_workspaces.split(',') if v.strip()}:raise HTTPException(403,'Sheets export is restricted to approved pilot workspaces.')
    if c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]<(1011 if get_settings().database_schema_profile=='intent-radar-v1' else 53):raise HTTPException(503,'The spreadsheet worker schema is not ready.')
    return ctx

def status(c):
    ctx=admin(c)
    row=c.execute('SELECT * FROM organization_integrations WHERE organization_id=? AND provider=?',(ctx.organization_id,service.PROVIDER)).fetchone()
    item=service.view(dict(row)) if row else None
    health='Not Connected'
    if item and item['status']!='DISCONNECTED':
        health='Verification Required'
        if item['status']=='REAUTH_REQUIRED' or item['last_error_code']:health='Connection Error'
        elif item['status']=='CONNECTED' and service.WRITE_SCOPE in item['scopes'] and item['last_success_at'] and item['connected_at'] and item['last_success_at']>=item['connected_at']:
            age=datetime.now(timezone.utc)-datetime.fromisoformat(item['last_success_at']);health='Connected' if timedelta(0)<=age<timedelta(minutes=15) else 'Health Unknown'
    try:oauth_spec();configured=service.configured()
    except HTTPException:configured=False
    return {'configured':configured,'connection':item,'health':health}

def describe(row):
    return {k:row[k] for k in ('id','status','row_count','sheet_title','target_range','spreadsheet_id','fingerprint','last_error_code','created_at','expires_at','attempts')}

def rows_for(c,selection):
    snap=exports.snapshot(c,selection)
    fields=exports.columns(snap)
    return [list(fields)]+[[rec.get(k,'') for k in fields] for rec in snap['records']]

def digest(sid,target,rows):return hashlib.sha256(json.dumps([sid,target,rows],ensure_ascii=False).encode()).hexdigest()

def target_for(body,rows):
    from openpyxl.utils import get_column_letter
    return "'"+body.sheet.replace("'","''")+"'!A"+str(body.start_row)+':'+get_column_letter(len(rows[0]))+str(body.start_row+len(rows)-1)

def cell_hash(values):return hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

async def preview(c,key,body):
    from app.integrations.google_sheets import reader_for
    ctx=admin(c);conn=sheet_exports.connection(c,key);sid=spreadsheet_id(body.spreadsheet);rows=rows_for(c,body.selection);target=target_for(body,rows)
    raw=await reader_for(key,conn['revision'])(c,ctx.actor,sid+'/values/'+quote(target,safe=''),{'valueRenderOption':'FORMULA','majorDimension':'ROWS'})
    if not isinstance(raw,dict) or not isinstance(raw.get('range'),str):raise HTTPException(502,'Could not confirm the destination range.')
    before=raw.get('values',[])
    if not isinstance(before,list) or len(before)>len(rows) or any(not isinstance(r,list) or len(r)>len(rows[0]) for r in before):raise HTTPException(409,'Sheet range response exceeded the reviewed dimensions.')
    sheet_exports.connection(c,key,conn['revision'])
    return stage(c,key,body,prior=before,expected_target=target)

def stage(c,key,body,*,prior,expected_target):
    ctx=admin(c);service.lock(c);conn=sheet_exports.connection(c,key);sid=spreadsheet_id(body.spreadsheet)
    rows=rows_for(c,body.selection);target=target_for(body,rows)
    if target!=expected_target:raise HTTPException(409,'Export size changed. Preview the destination again.')
    baseline=cell_hash(prior);fingerprint=digest(sid,target,[baseline,rows]);ident=str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id+':radar-sheets:'+str(body.request_id)))
    selection=json.dumps({'version':2,'before':baseline,'selection':body.selection.model_dump(mode='json')})
    old=c.execute('SELECT * FROM radar_sheet_exports WHERE organization_id=? AND id=?',(ctx.organization_id,ident)).fetchone()
    if old:
        if old['fingerprint']!=fingerprint or old['created_by']!=ctx.actor or old['connection_id']!=key or old['connection_revision']!=conn['revision']:raise HTTPException(409,'This request already refers to a different review.')
    else:
        cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        if c.execute('SELECT COUNT(*) FROM radar_sheet_exports WHERE organization_id=? AND created_at>?',(ctx.organization_id,cutoff)).fetchone()[0]>=20:raise HTTPException(429,'Hourly export review limit reached.')
        stamp=now();expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        c.execute('INSERT INTO radar_sheet_exports(id,organization_id,connection_id,connection_revision,created_by,request_id,fingerprint,selection_json,spreadsheet_id,sheet_title,target_range,row_count,created_at,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(ident,ctx.organization_id,key,conn['revision'],ctx.actor,str(body.request_id),fingerprint,selection,sid,body.sheet,target,len(rows)-1,stamp,expires,stamp));service.audit(c,ident,'RADAR_SHEETS_STAGED')
    return describe(sheet_exports.owned(c,ident))|{'columns':rows[0],'preview':rows[1:6],'existing_cells':sum(v!='' for r in prior for v in r),'existing_preview':[r[:len(rows[0])] for r in prior[:5]]}

def verified_rows(c,row):
    ctx=admin(c)
    if row['created_by']!=ctx.actor:raise HTTPException(403,'Only the reviewing administrator can authorize this write.')
    envelope=json.loads(row['selection_json'])
    if envelope.get('version')!=2:raise HTTPException(409,'This review predates destination verification. Prepare a fresh preview.')
    rows=rows_for(c,exports.Selection.model_validate(envelope['selection']))
    if digest(row['spreadsheet_id'],row['target_range'],[envelope['before'],rows])!=row['fingerprint']:raise HTTPException(409,'Evidence changed. Prepare a fresh review.')
    return rows
