"""Signed-in administration. Plain API credentials are shown only once, never stored."""
from uuid import UUID
from fastapi import APIRouter,Depends,Response
from app.api.dependencies import get_db
from app.developer import keys
router=APIRouter(prefix='/organization/developer',tags=['Developer settings'])
@router.get('/status')
def status(c=Depends(get_db,scope='function')):
    from app.config.settings import get_settings
    from app.api.organization import membership_role
    from app.people.service import ctx
    context=ctx(c)
    return {'enabled':get_settings().heysow_developer_api_enabled,'can_manage':membership_role(c,context.actor,context.organization_id) in ('OWNER','ADMIN'),'api_version':'v1','authentication':'SCOPED_BEARER_KEY','credentials_shown_once':True,'mcp_available':get_settings().heysow_mcp_enabled,'webhooks_available':get_settings().heysow_webhooks_enabled}
@router.get('/keys')
def listing(response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return keys.listing(c)
@router.get('/usage')
def usage(response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return keys.usage_telemetry(c)
@router.get('/openapi')
def developer_openapi(c=Depends(get_db,scope='function')):
    keys.manager(c)
    from app.api.routes.public_v1 import openapi_document
    return openapi_document()
@router.post('/diagnostics')
def diagnostics(response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store'
    from app.config.settings import get_settings
    from app.intent_radar import tools as radar_tools
    from app.api.routes.public_v1 import openapi_document
    ctx_info=keys.manager(c)
    key_listing=keys.listing(c)
    telemetry=keys.usage_telemetry(c)
    spec=openapi_document()
    s=get_settings()
    mcp_tools=list(radar_tools.READ.keys())+list(radar_tools.EXTENDED_READ.keys())+(list(radar_tools.GROWTH_READ.keys()) if s.intent_radar_growth_enabled else [])
    return {
        'ok':bool(s.heysow_developer_api_enabled),
        'checked_at':keys.now(),
        'workspace_id':ctx_info.organization_id,
        'rest_api':{'enabled':bool(s.heysow_developer_api_enabled),'base_path':'/api/v1','openapi_path':'/api/v1/openapi.json','endpoint_count':len(spec.get('paths',{})),'rate_limit_per_minute':s.developer_key_requests_per_minute},
        'mcp':{'enabled':bool(s.heysow_mcp_enabled),'endpoint_path':'/api/v1/mcp','transport':'Streamable HTTP (stateless JSON-RPC)','authentication':'Scoped Bearer API key (Authorization: Bearer pbk_...)','oauth_2_1_supported':False,'oauth_note':'Static scoped Bearer API keys are supported for Streamable HTTP MCP clients (Claude Code, Cursor, Codex, MCP Inspector). OAuth 2.1 Authorization Server / Dynamic Client Registration is not currently deployed.','tools':mcp_tools,'resources':['planebyte://workspace/context','planebyte://sources/catalog','planebyte://sources/policies']},
        'available_scopes':key_listing['available_scopes'],
        'active_keys':telemetry['keys']['active'],
        'last_used_at':telemetry['keys']['last_used_at'],
    }
@router.post('/keys',status_code=201)
def create(body:keys.Create,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return keys.create(c,body)
@router.post('/keys/{key}/rotate')
def rotate(key:UUID,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return keys.rotate(c,str(key))
@router.delete('/keys/{key}')
def revoke(key:UUID,c=Depends(get_db,scope='function')):return keys.revoke(c,str(key))

@router.get('/approvals')
def approvals(page:int=1,c=Depends(get_db,scope='function')):
    from app.developer.approvals import listing
    if not 1<=page<=10000:
        from fastapi import HTTPException
        raise HTTPException(422,'Choose a valid page.')
    return listing(c,page)
from pydantic import BaseModel,ConfigDict
from typing import Literal
class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['approve','decline']
@router.post('/approvals/{key}')
async def approve(key:UUID,body:Approval,c=Depends(get_db,scope='function')):
    from app.developer.approvals import decide
    result=decide(c,str(key),body.decision);c.commit()
    job=result.get('result',{}).get('job')
    if job:
        from app.intelligence.dispatch import launch
        await launch(job['id'])
    return result
