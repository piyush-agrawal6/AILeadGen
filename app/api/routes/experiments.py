"""Owner-controlled experiment operations; all send decisions use existing guards."""
import json
from typing import Literal
from fastapi import APIRouter,Depends,Request,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.api.permissions import require_owner
from app.database.experiment_schema import ready
from app.experiments import service
from app.experiments.plan import EXPERIMENT_ID
router=APIRouter(prefix='/experiments',tags=['Five-day experiment'])
def schema(c):
 if not ready(c):raise HTTPException(503,'Experiment schema has not been deployed.')
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
@router.post('/setup')
def setup(request:Request,c=Depends(get_db,scope='function')):require_owner(c,request.state.user_email);return service.setup(c,request.state.user_email)
@router.get('/current')
def current(c=Depends(get_db,scope='function')):
 schema(c)
 from app.experiments.analytics import dashboard
 return dashboard(c)
@router.get('/members')
def members(page:int=Query(1,ge=1),state:str=Query('',max_length=30),day:int=Query(0,ge=0,le=5),c=Depends(get_db,scope='function')):
 schema(c);where='a.experiment_id=?';args=[EXPERIMENT_ID]
 if state:where+=' AND a.state=?';args.append(state)
 if day:where+=' AND a.experiment_day=?';args.append(day)
 base=' FROM experiment_members a JOIN businesses b ON b.id=a.business_id WHERE '+where
 return {'items':[dict(r) for r in c.execute('SELECT a.*,b.name company'+base+' ORDER BY a.created_at DESC LIMIT 25 OFFSET ?',[*args,(page-1)*25]).fetchall()],'total':c.execute('SELECT COUNT(*)'+base,args).fetchone()[0],'page':page,'page_size':25}
@router.get('/catalog')
def catalog(c=Depends(get_db,scope='function')):
 schema(c)
 from app.experiments.catalog import status
 return status(c)
@router.post('/catalog')
async def catalog_upload(request:Request,c=Depends(get_db,scope='function')):
 schema(c);require_owner(c,request.state.user_email)
 from app.experiments.catalog import upload
 raw=await request.body()
 try:return upload(c,raw,request.state.user_email)
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
class CatalogSettings(Strict):
 attach_enabled:bool=False
 mode:Literal['BRIEF_ONLY','BRIEF_PLUS_CATALOG','CATALOG_LINK']='BRIEF_ONLY'
 public_url:str|None=Field(None,max_length=500)
@router.put('/catalog')
def catalog_config(body:CatalogSettings,request:Request,c=Depends(get_db,scope='function')):
 schema(c);require_owner(c,request.state.user_email)
 from app.experiments.catalog import status
 from app.reports.data import public_url
 from app.database.prospects import now
 old=status(c)
 configured='CONFIGURED' if old.get('object_key') or (body.mode=='CATALOG_LINK' and public_url(body.public_url)) else 'NOT_CONFIGURED'
 if body.attach_enabled and body.mode=='BRIEF_PLUS_CATALOG' and not old.get('object_key'):raise HTTPException(422,'Upload the catalog before enabling attachment.')
 if body.mode=='CATALOG_LINK' and not public_url(body.public_url):raise HTTPException(422,'Configure a public catalog link.')
 c.execute("INSERT INTO experiment_catalog(id,version,status,attach_enabled,mode,public_url,updated_at,updated_by) VALUES(1,0,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,attach_enabled=excluded.attach_enabled,mode=excluded.mode,public_url=excluded.public_url,updated_at=excluded.updated_at,updated_by=excluded.updated_by",(configured,int(body.attach_enabled),body.mode,body.public_url,now(),request.state.user_email));return status(c)
class Reply(Strict):disposition:Literal['POSITIVE','QUESTION','NOT_NOW','NEGATIVE','UNSUBSCRIBE','OUT_OF_OFFICE','UNKNOWN'];inbound_message_id:str|None=None
@router.put('/members/{mid}/reply')
def reply(mid:str,body:Reply,request:Request,c=Depends(get_db,scope='function')):
 schema(c);service.reply(c,mid,body.disposition,request.state.user_email,inbound_id=body.inbound_message_id,manual=True);return {'saved':True,'auto_reply_sent':False}
class Conversion(Strict):status:Literal['NO_REPLY','REPLIED','POSITIVE_REPLY','MEETING','PROPOSAL_REQUESTED','WON','LOST']
@router.put('/members/{mid}/conversion')
def conversion(mid:str,body:Conversion,c=Depends(get_db,scope='function')):
 schema(c);c.execute('UPDATE experiment_members SET conversion_status=? WHERE id=?',(body.status,mid));return {'saved':True}
@router.post('/activate')
def activate(request:Request,c=Depends(get_db,scope='function')):
 schema(c);return service.activate(c,request.state.user_email)
@router.post('/pause')
def pause(request:Request,c=Depends(get_db,scope='function')):
 schema(c);require_owner(c,request.state.user_email);c.execute("UPDATE experiments SET status='PAUSED',send_approved=0 WHERE id=?",(EXPERIMENT_ID,));return {'status':'PAUSED','inbox_sync_unchanged':True}

@router.get('/copy-generation')
def copy_status(c=Depends(get_db,scope='function')):
 schema(c)
 from app.experiments.copy_batch import status
 return status(c)

@router.post('/copy-health')
async def copy_health(request:Request,c=Depends(get_db,scope='function')):
 schema(c);require_owner(c,request.state.user_email)
 from app.experiments.copy_batch import synthetic_leads,generate_personalized_copy_batch,status
 # An explicit owner check uses one synthetic lead; ordinary page loads do not
 # spend provider quota or bypass a provider cooldown.
 result=await generate_personalized_copy_batch(c,synthetic_leads(c,1),request.state.user_email,health_probe=True,force=True)
 good=result['metrics'].get('ai_generated_leads')==1 and not result['metrics'].get('deterministic_fallback_leads')
 current=status(c)
 return {'provider':next(iter(result['results'].values())).get('copy_provider',current['provider']),'model':current['model'],'status':'READY' if good else 'BLOCKED','api_key_configured':current['api_key_configured'],'batch_size':current['batch_size']}
