"""Optional, review-first source endpoints; existing scans and outreach are independent."""
import asyncio,json,uuid,csv,io,re
from typing import Literal
from pydantic import Field
from fastapi import APIRouter,Depends,Request,HTTPException,Query,BackgroundTasks
from fastapi.responses import Response
from app.api.dependencies import get_db
from app.api.permissions import require_owner
from app.acquisition.models import Strict,SearchIntent,Budgets,ProcessingOptions,ColumnMapping
from app.acquisition.config import settings,require
from app.acquisition import service,ai,sheets
from app.acquisition.firecrawl import FirecrawlLeadSource,SourceUnavailable
from app.acquisition.imports import ImportInvalid,Spreadsheet,suggested_mapping
from app.acquisition.dispatch import launch
from app.database.prospects import now
from app.database.acquisition_schema import ready
from app.acquisition import preferences as workspace_preferences
router=APIRouter(prefix='/acquisition',tags=['Optional acquisition'])

class Preferences(Strict):
    enabled:dict[Literal['ai','firecrawl','import','sheets'],bool]=Field(default_factory=lambda:{'ai':True,'firecrawl':True,'import':True,'sheets':True})
    budgets:Budgets=Field(default_factory=Budgets)

@router.get('/settings')
def status(request:Request,c=Depends(get_db,scope='function')):
    s=settings();prefs=Preferences.model_validate(workspace_preferences.load(c)) if ready(c) else Preferences()
    health={r['provider']:dict(r) for r in c.execute('SELECT provider,status,checked_at,error_code FROM acquisition_provider_health').fetchall()} if ready(c) else {}
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    internal=request.state.organization_id==PLANEBYTE_ORGANIZATION_ID
    connected=internal and bool(c.execute('SELECT 1 FROM acquisition_google_connections WHERE actor=?',(request.state.user_email,)).fetchone()) if ready(c) else False
    if not internal:health={}
    from app.config.settings import get_settings
    workspace_sheets=bool(get_settings().heysow_customer_integrations_enabled and s.enable_import and s.enable_sheets and c.execute("SELECT 1 FROM organization_integrations WHERE organization_id=? AND provider='GOOGLE_SHEETS' AND status='CONNECTED'",(request.state.organization_id,)).fetchone())
    return {'workspace_sheets_available':workspace_sheets,'features':{'ai':s.enable_ai and prefs.enabled.get('ai',True),'firecrawl':s.enable_firecrawl and prefs.enabled.get('firecrawl',True),'import':s.enable_import and prefs.enabled.get('import',True),'sheets':internal and s.enable_sheets and prefs.enabled.get('sheets',True)},'provider_tests_available':internal,'environment_flags':{'ai':s.enable_ai,'firecrawl':s.enable_firecrawl,'import':s.enable_import,'sheets':s.enable_sheets},'configured':{'ai':bool(s.vertex_enabled or s.gemini_key.get_secret_value()),'firecrawl':bool(s.firecrawl_key.get_secret_value()),'sheets':internal and bool(s.google_id and s.google_secret.get_secret_value())},'model':s.vertex_model if s.primary_provider=='vertex' else s.gemini_model,'provider':s.primary_provider,'firecrawl_endpoint':s.firecrawl_url,'health':health,'preferences':prefs.model_dump(),'google_sheets_connected':connected,'google_sheets_scope':sheets.SCOPE,'google_sheets_redirect_uri':s.sheets_redirect_uri,'import_limits':{'bytes':1_000_000,'rows':10_000,'columns':50},'schema_ready':ready(c)}

@router.put('/settings')
def save_preferences(body:Preferences,request:Request,c=Depends(get_db,scope='function')):
    require_owner(c,request.state.user_email)
    workspace_preferences.save(c,request.state.user_email,body.model_dump())
    return {'saved':True,'existing_scans_and_outreach_unchanged':True}

@router.post('/providers/{provider}/test')
async def test_provider(provider:Literal['vertex','gemini','firecrawl'],request:Request,c=Depends(get_db,scope='function')):
    require_owner(c,request.state.user_email);s=settings();metadata={};error=None
    try:
        if provider=='firecrawl':metadata=await FirecrawlLeadSource(s).health()
        elif provider=='vertex':
            from app.acquisition.vertex import VertexAIProvider
            intent=await VertexAIProvider(s).parse_lead_search_intent('Find 5 dentists in Bristol UK with website and SEO opportunities.')
            if intent.targetQualifiedLeads!=5 or intent.verticals!=['dentists'] or intent.cities!=['Bristol']:raise ai.AiOutputError('Controlled Vertex intent did not match.')
            metadata={'model':s.vertex_model,'project':s.vertex_project,'location':s.vertex_location,'authentication':'SERVICE_IDENTITY','structured_output_verified':True}
        else:
            if not s.gemini_key.get_secret_value():raise ai.AiUnavailable('Gemini is not configured.')
            intent=await ai.GeminiInstructionProvider(s).parse_lead_search_intent('Find 5 dentists in Bristol UK with website and SEO opportunities.')
            if intent.targetQualifiedLeads!=5 or intent.verticals!=['dentists'] or intent.cities!=['Bristol']:raise ai.AiUnavailable('Controlled intent did not match the requested search.')
            metadata={'model':s.gemini_model,'structured_output_verified':True}
        state='HEALTHY'
    except Exception:state='ERROR';error='PROVIDER_CONNECTION_FAILED'
    c.execute('INSERT INTO acquisition_provider_health(provider,status,checked_at,error_code) VALUES(?,?,?,?) ON CONFLICT(provider) DO UPDATE SET status=excluded.status,checked_at=excluded.checked_at,error_code=excluded.error_code',(provider,state,now(),error))
    return {'provider':provider,'status':state,'error_code':error,**metadata}

class IntentRequest(Strict):prompt:str=Field(min_length=5,max_length=2000)
@router.post('/intent')
async def interpret(body:IntentRequest,request:Request,c=Depends(get_db,scope='function')):
    require('ai',c)
    try:
        result,hit=await ai.cached(c,request.state.user_email,'LEAD_INTENT',{'prompt':body.prompt},lambda:ai.provider(c).parse_lead_search_intent(body.prompt),SearchIntent,validator=lambda value:ai.validate_intent(body.prompt,value))
        return {'intent':result.model_dump(),'cached':hit,'requires_review':True,'acquisition_started':False}
    except ai.AiUnavailable as exc:raise HTTPException(503,{'code':'AI_INTERPRETATION_UNAVAILABLE','message':str(exc),'manual_filters_available':True}) from None

class SearchStart(Strict):
    request_id:str=Field(default_factory=lambda:str(uuid.uuid4()),pattern=r'^[a-f0-9-]{36}$')
    name:str=Field('',max_length=120)
    original_prompt:str=Field('',max_length=2000)
    intent:SearchIntent
    reviewed:Literal[True]
    interpretation_mode:Literal['AI','MANUAL']='AI'
    budgets:Budgets=Field(default_factory=Budgets)
    lighthouse:bool=False
    qualification_mode:Literal['CONTACTABLE_ONLY','ANALYZED','STRICT']='CONTACTABLE_ONLY'
@router.post('/firecrawl',status_code=201)
def start_search(body:SearchStart,request:Request,background:BackgroundTasks,c=Depends(get_db,scope='function')):
    require('firecrawl',c)
    if body.interpretation_mode=='AI':require('ai',c)
    from app.workflows.controls import require_unpaused
    require_unpaused(c,'scan')
    p=ProcessingOptions(qualification_mode=body.qualification_mode,default_country=body.intent.countries[0],default_city=body.intent.cities[0] if len(body.intent.cities)==1 else '',default_vertical=body.intent.verticals[0],lighthouse=body.lighthouse,analyze_websites=True,analyze_seo=True,analyze_security=True)
    configuration={'intent':body.intent.model_dump(),'budgets':body.budgets.model_dump(),'processing':p.model_dump()};origin={'original_prompt':body.original_prompt,'interpretation_mode':body.interpretation_mode,'queries':body.intent.queries}
    r=service.create_job(c,'FIRECRAWL',request.state.user_email,body.request_id,configuration,origin);cid=service.create_campaign(c,r['id'],body.name or ' / '.join(body.intent.cities or body.intent.countries)+' · Firecrawl',body.original_prompt)
    service.event(c,r['id'],'SEARCH_PLAN','Reviewed search plan stored. No outreach is automatically created.');c.commit();background.add_task(launch,r['id']);return {'id':r['id'],'campaign_id':cid,'status':r['status']}

@router.post('/imports/files',status_code=201)
async def upload(request:Request,filename:str=Query(min_length=1,max_length=180),request_id:str=Query(pattern=r'^[a-f0-9-]{36}$'),c=Depends(get_db,scope='function')):
    require('import',c);raw=await request.body()
    try:return await asyncio.to_thread(service.stage_file,c,request.state.user_email,filename,raw,request_id)
    except (ImportInvalid,ValueError) as exc:raise HTTPException(422,str(exc)) from None

class SheetChoice(Strict):sheet:str=Field(min_length=1,max_length=100)
@router.post('/imports/{jid}/sheet')
def select_sheet(jid:str,body:SheetChoice,request:Request,c=Depends(get_db,scope='function')):
    require('import',c)
    try:return service.inspect_sheet(c,jid,request.state.user_email,body.sheet)
    except ImportInvalid as exc:raise HTTPException(422,str(exc)) from None

@router.post('/imports/{jid}/mapping/suggest')
async def mapping_suggestion(jid:str,request:Request,c=Depends(get_db,scope='function')):
    require('import',c);r=service.job(c,jid,request.state.user_email)
    if r['status']!='MAPPING_REVIEW':raise HTTPException(409,'Import mapping was already approved.')
    manifest=json.loads(r['manifest_json']);columns=manifest['headers'];sample=ai.sanitized_sample(manifest['sample']);mapping=suggested_mapping(columns);method='HEADER_SUGGESTION';warning=None
    try:
        require('ai',c)
        value={'headers':columns,'sheet':manifest['sheet'],'sample':sample}
        mapping,hit=await ai.cached(c,request.state.user_email,'IMPORT_MAPPING',value,lambda:ai.provider(c).interpret_import_schema(columns,manifest['sheet'],manifest['sample']),ColumnMapping,validator=lambda result:result.validate_headers(columns));mapping.validate_headers(columns);method='AI';cached=hit
    except (ai.AiUnavailable,ValueError,HTTPException):warning='AI interpretation unavailable. Review the labelled header suggestions or map columns manually.';cached=False
    return {'mapping':mapping.model_dump(),'method':method,'warning':warning,'cached':cached,'requires_review':True,'rows_processed_by_ai':0}

class ImportApproval(Strict):
    mapping:ColumnMapping
    processing:ProcessingOptions=Field(default_factory=ProcessingOptions)
    name:str=Field('',max_length=120)
    request_id:str=Field(default_factory=lambda:str(uuid.uuid4()),pattern=r'^[a-f0-9-]{36}$')
    reviewed:Literal[True]
@router.post('/imports/{jid}/approve')
def import_review(jid:str,body:ImportApproval,request:Request,background:BackgroundTasks,c=Depends(get_db,scope='function')):
    require('import',c);r=service.job(c,jid,request.state.user_email)
    if r['source_type']=='GOOGLE_SHEETS':require('sheets',c)
    from app.workflows.controls import require_unpaused
    require_unpaused(c,'scan')
    try:result=service.approve_import(c,jid,request.state.user_email,body.mapping,body.processing,body.name,body.request_id)
    except (ImportInvalid,ValueError) as exc:raise HTTPException(422,str(exc)) from None
    c.commit();background.add_task(launch,jid);return result

@router.get('/jobs/{jid}')
def progress(jid:str,page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return service.detail(c,jid,page,page_size)

@router.post('/jobs/{jid}/retry')
def retry(jid:str,request:Request,background:BackgroundTasks,c=Depends(get_db,scope='function')):
    r=service.job(c,jid,request.state.user_email);require('firecrawl' if r['source_type']=='FIRECRAWL' else 'import',c)
    if r['source_type']=='GOOGLE_SHEETS':require('sheets',c)
    from app.workflows.controls import require_unpaused
    require_unpaused(c,'scan');result=service.retry(c,jid,request.state.user_email);c.commit();background.add_task(launch,jid);return result

@router.get('/jobs/{jid}/issues.csv')
def issues_export(jid:str,request:Request,c=Depends(get_db,scope='function')):
    service.job(c,jid,request.state.user_email);from app.exports.phase3 import safe_cell
    out=io.StringIO();writer=csv.writer(out);writer.writerow(['Row','Reason','Source values'])
    for r in c.execute('SELECT row_number,reason,values_json FROM acquisition_issues WHERE job_id=? ORDER BY row_number LIMIT 10000',(jid,)).fetchall():writer.writerow([safe_cell(r['row_number']),safe_cell(r['reason']),safe_cell(r['values_json'])])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="import-issues.csv"','Cache-Control':'no-store'})

@router.post('/sheets/authorize')
def authorize(request:Request,c=Depends(get_db,scope='function')):
    require_owner(c,request.state.user_email)
    try:return sheets.start(c,request.state.user_email)
    except sheets.SheetsUnavailable as exc:raise HTTPException(503,str(exc)) from None
class GoogleCode(Strict):
    state:str=Field(min_length=20,max_length=100)
    code:str=Field(min_length=5,max_length=3000)
@router.post('/sheets/connect')
async def connect(body:GoogleCode,request:Request,c=Depends(get_db,scope='function')):
    require_owner(c,request.state.user_email)
    try:return await sheets.connect(c,request.state.user_email,body.state,body.code)
    except sheets.SheetsUnavailable as exc:raise HTTPException(503,str(exc)) from None
@router.delete('/sheets/connection')
def disconnect(request:Request,c=Depends(get_db,scope='function')):
    c.execute('DELETE FROM acquisition_google_connections WHERE actor=?',(request.state.user_email,));return {'disconnected':True,'scope':sheets.SCOPE}
@router.get('/sheets/metadata')
async def sheet_metadata(request:Request,spreadsheet:str=Query(min_length=10,max_length=500),c=Depends(get_db,scope='function')):
    require('sheets',c)
    try:return await sheets.metadata(c,request.state.user_email,spreadsheet)
    except (sheets.SheetsUnavailable,ImportInvalid) as exc:raise HTTPException(422,str(exc)) from None
class SheetImport(Strict):
    spreadsheet:str=Field(min_length=10,max_length=500)
    sheet:str=Field(min_length=1,max_length=100)
    request_id:str=Field(default_factory=lambda:str(uuid.uuid4()),pattern=r'^[a-f0-9-]{36}$')
@router.post('/sheets/imports',status_code=201)
async def stage_sheet(body:SheetImport,request:Request,c=Depends(get_db,scope='function')):
    require('import',c);require('sheets',c)
    try:return await sheets.stage(c,request.state.user_email,body.spreadsheet,body.sheet,body.request_id)
    except (sheets.SheetsUnavailable,ImportInvalid) as exc:raise HTTPException(422,str(exc)) from None

@router.get('/leads/{pid}/sources')
def lead_sources(pid:str,c=Depends(get_db,scope='function')):
    current=[{**dict(r),'fields':json.loads(r['field_sources_json'])} for r in c.execute('SELECT id,business_id,campaign_id,source_type,source_url,field_sources_json,observed_at FROM lead_source_evidence WHERE prospect_id=? ORDER BY observed_at DESC',(pid,)).fetchall()]
    legacy=[{'id':'maps-'+str(r['id']),'business_id':r['id'],'campaign_id':r['campaign_id'],'source_type':'OVERTURE','source_url':None,'observed_at':r['created_at'],'fields':{'discovery':{'source_overture':bool(r['source_overture']),'source_osm':bool(r['source_osm']),'verification':'EXISTING_PROVIDER_RECORD'}}} for r in c.execute('SELECT b.id,b.created_at,b.source_overture,b.source_osm,r.campaign_id FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=? AND (b.source_overture=1 OR b.source_osm=1)',(pid,)).fetchall()]
    return {'prospect_id':pid,'evidence':current+legacy,'source_types':sorted({r['source_type'] for r in current+legacy})}
