from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from app.api.dependencies import get_db
from app.api.routes.integrations import Code,ExportApproval
from app.integrations import google_sheets,radar_sheets as radar,service,sheet_exports as jobs

db=Depends(get_db,scope='function')
router=APIRouter(prefix='/intent-radar/sheets',tags=['Radar spreadsheet exports'])

@router.get('')
def status(c=db):return radar.status(c)

@router.post('/authorize')
def authorize(c=db):
    radar.admin(c);return service.authorize(c,write=True,spec=radar.oauth_spec())

@router.post('/connect')
async def connect(body:Code,c=db):
    radar.admin(c);return await service.connect(c,body.state,body.code,spec=radar.oauth_spec())

@router.delete('/connections/{key}')
def disconnect(key:UUID,c=db):
    radar.admin(c);return service.disconnect(c,str(key))

@router.post('/connections/{key}/inspect')
async def inspect(key:UUID,body:dict[str,str],c=db):
    radar.admin(c);return await google_sheets.metadata(c,str(key),body.get('spreadsheet',''))

@router.post('/connections/{key}/exports')
async def stage(key:UUID,body:radar.Draft,c=db):
    radar.admin(c);meta=await google_sheets.metadata(c,str(key),body.spreadsheet)
    if not any(t['title']==body.sheet for t in meta['tabs']):raise HTTPException(422,'Select an existing worksheet.')
    return radar.stage(c,str(key),body)

@router.get('/history')
def history(c=db):
    ctx=radar.admin(c)
    return {'items':[radar.describe(row) for row in c.execute('SELECT * FROM radar_sheet_exports WHERE organization_id=? AND created_by=? ORDER BY created_at DESC LIMIT 25',(ctx.organization_id,ctx.actor)).fetchall()]}

@router.post('/exports/{key}/{action}')
async def control(key:UUID,action:Literal['approve','retry','cancel'],body:ExportApproval|None=None,c=db):
    radar.admin(c)
    if key.version!=5:raise HTTPException(404,'Review not found.')
    if action=='cancel':return jobs.cancel(c,str(key))
    if not body:raise HTTPException(422,'Confirm the exact reviewed overwrite.')
    result=(jobs.approve if action=='approve' else jobs.retry)(c,str(key),body.review_digest,body.confirmation);c.commit()
    if result['status']=='QUEUED':await jobs.launch(str(key))
    return result
