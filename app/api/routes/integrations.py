"""Customer connections are scoped separately from existing internal accounts."""
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from fastapi import APIRouter,Depends,Query,Response
from app.api.dependencies import get_db
from app.integrations import service,google_sheets,sheet_exports

router=APIRouter(prefix='/organization/integrations',tags=['Workspace integrations'],dependencies=[Depends(service.require_enabled)])

class Code(BaseModel):
    model_config=ConfigDict(extra='forbid')
    state:str=Field(pattern=r'^hsw_[A-Za-z0-9_-]{43}$')
    code:str=Field(min_length=5,max_length=3000)

class Connection(BaseModel):
    id:UUID
    provider:Literal['GOOGLE_SHEETS']
    status:Literal['NOT_CONNECTED','CONNECTED','REAUTH_REQUIRED','DISCONNECTED']
    revision:int
    connected_by:str|None
    connected_at:str|None
    last_success_at:str|None
    last_error_code:str|None
    scopes:list[str]

class Connections(BaseModel):
    items:list[Connection]
    can_manage:bool
    google_sheets_configured:bool
    google_sheets_import_enabled:bool=False
    google_sheets_scope:str

@router.get('',response_model=Connections)
def listing(c=Depends(get_db,scope='function')):return service.listing(c)

@router.post('/google-sheets/authorize')
def authorize(response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store'
    return service.authorize(c)

@router.post('/google-sheets/authorize-export')
def authorize_export(response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store'
    return service.authorize(c,write=True)

@router.post('/google-sheets/connect',response_model=Connection)
async def connect(body:Code,c=Depends(get_db,scope='function')):return await service.connect(c,body.state,body.code)

@router.delete('/{connection_id}')
def disconnect(connection_id:UUID,c=Depends(get_db,scope='function')):return service.disconnect(c,str(connection_id))

@router.get('/{connection_id}/sheets')
async def sheet_metadata(connection_id:UUID,spreadsheet:str=Query(min_length=10,max_length=500),c=Depends(get_db,scope='function')):
    return await google_sheets.metadata(c,str(connection_id),spreadsheet)

class SheetImport(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    spreadsheet:str=Field(min_length=10,max_length=500)
    sheet:str=Field(min_length=1,max_length=100)
    request_id:UUID
@router.post('/{connection_id}/sheets/import',status_code=201)
async def import_sheet(connection_id:UUID,body:SheetImport,c=Depends(get_db,scope='function')):
    from app.acquisition.imports import ImportInvalid
    from fastapi import HTTPException
    try:return await google_sheets.stage_import(c,str(connection_id),body.spreadsheet,body.sheet,body.request_id)
    except ImportInvalid as exc:raise HTTPException(422,str(exc)) from None

@router.get('/{connection_id}/sheets/exports')
def exports(connection_id:UUID,c=Depends(get_db,scope='function')):return sheet_exports.listing(c,str(connection_id))

@router.post('/{connection_id}/sheets/exports',status_code=201)
def stage_export(connection_id:UUID,body:sheet_exports.Export,c=Depends(get_db,scope='function')):
    from app.acquisition.imports import ImportInvalid
    from fastapi import HTTPException
    try:return sheet_exports.stage(c,str(connection_id),body)
    except ImportInvalid as exc:raise HTTPException(422,str(exc)) from None

class ExportApproval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    review_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    confirmation:Literal['OVERWRITE_REVIEWED_RANGE']

@router.post('/sheets/exports/{export_id}/approve')
async def approve_export(export_id:UUID,body:ExportApproval,c=Depends(get_db,scope='function')):
    result=sheet_exports.approve(c,str(export_id),body.review_digest,body.confirmation);c.commit()
    if result['status']=='QUEUED':await sheet_exports.launch(str(export_id))
    return result

@router.post('/sheets/exports/{export_id}/retry')
async def retry_export(export_id:UUID,body:ExportApproval,c=Depends(get_db,scope='function')):
    result=sheet_exports.retry(c,str(export_id),body.review_digest,body.confirmation);c.commit();await sheet_exports.launch(str(export_id));return result

@router.post('/sheets/exports/{export_id}/cancel')
def cancel_export(export_id:UUID,c=Depends(get_db,scope='function')):return sheet_exports.cancel(c,str(export_id))
