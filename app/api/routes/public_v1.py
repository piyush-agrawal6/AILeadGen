"""Versioned external contracts over existing authorized domain services."""
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,Query,Header,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.developer.keys import require
from app.prospecting import tools
router=APIRouter(prefix='/v1',tags=['Public Lead Engine API v1'])

@router.get('/intent-radar/workspace',dependencies=[Depends(lambda:require('intent:read'))])
def intent_workspace(c=Depends(get_db,scope='function')):
    from app.intent_radar.operations import workspace_context
    return workspace_context(c)

@router.get('/intent-radar/sources',dependencies=[Depends(lambda:require('intent:read'))])
def intent_sources(c=Depends(get_db,scope='function')):
    from app.intent_radar import connectors,operations
    return {'items':connectors.catalog(c),'health':operations.source_health(c)['items']}

@router.get('/intent-radar/signals',dependencies=[Depends(lambda:require('intent:read'))])
def intent_signals(
    search:str=Query('',max_length=120),
    source:str=Query('',max_length=40),
    category:str=Query('',max_length=50),
    status:str=Query('',max_length=30),
    view:Literal['','all','needs_review','high_intent','saved','qualified','dismissed']='',
    min_score:int=Query(0,ge=0,le=100),
    buying_intent:Literal['','explicit','possible','none','insufficient','unassessed']='',
    from_date:str=Query('',max_length=20),
    to_date:str=Query('',max_length=20),
    sort:Literal['newest','oldest','score','score_asc','title']='newest',
    page:int=Query(1,ge=1,le=10000),
    page_size:int=Query(25,ge=1,le=100),
    cursor:str|None=Query(None,max_length=40),
    c=Depends(get_db,scope='function'),
):
    from app.intent_radar import service
    if cursor and cursor.isdigit():
        page=max(1,min(10000,int(cursor)))
    res=service.listing(
        c,'signals',
        page=page,size=page_size,search=search,source=source,category=category,status=status,
        view=view,min_score=min_score,buying_intent=buying_intent,
        from_date=from_date,to_date=to_date,sort=sort,
    )
    res['next_cursor']=str(page+1) if res.get('has_more') else None
    return res

@router.get('/intent-radar/signals/{key}',dependencies=[Depends(lambda:require('intent:read'))])
def intent_signal_detail(key:UUID,c=Depends(get_db,scope='function')):
    from app.intent_radar import service
    return service.get(c,'signals',str(key))

@router.get('/intent-radar/signals/{key}/analysis',dependencies=[Depends(lambda:require('intent:read'))])
def intent_signal_analysis(key:UUID,c=Depends(get_db,scope='function')):
    from app.intent_radar.intelligence import history
    return history(c,str(key))

@router.get('/intent-radar/discoveries',dependencies=[Depends(lambda:require('intent:read'))])
def intent_discoveries(
    search:str=Query('',max_length=120),
    source:str=Query('',max_length=40),
    status:str=Query('',max_length=30),
    sort:Literal['newest','oldest','title_asc','title_desc','results_desc','results_asc']='newest',
    page:int=Query(1,ge=1,le=10000),
    page_size:int=Query(20,ge=1,le=100),
    c=Depends(get_db,scope='function'),
):
    from app.intent_radar import discovery_workspace
    return discovery_workspace.list_discoveries(c,page=page,page_size=page_size,search=search,source=source,status=status,sort=sort)

@router.get('/intent-radar/discoveries/{key}',dependencies=[Depends(lambda:require('intent:read'))])
def intent_discovery_detail(key:UUID,c=Depends(get_db,scope='function')):
    from app.intent_radar import discovery_workspace
    return discovery_workspace.get_discovery(c,str(key))

@router.get('/intent-radar/saved-searches',dependencies=[Depends(lambda:require('intent:read'))])
def intent_saved_searches(search:str=Query('',max_length=120),page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    from app.intent_radar import discovery_workspace
    return discovery_workspace.list_saved_searches(c,search=search,page=page,page_size=page_size)

@router.get('/intent-radar/monitors',dependencies=[Depends(lambda:require('intent:read'))])
def intent_monitors(search:str=Query('',max_length=120),status:str=Query('',max_length=30),page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    from app.intent_radar import service
    return service.listing(c,'monitors',page=page,size=page_size,search=search,status=status)

@router.get('/intent-radar/monitors/{key}/runs',dependencies=[Depends(lambda:require('intent:read'))])
def intent_monitor_runs(key:UUID,c=Depends(get_db,scope='function')):
    import json
    from app.intent_radar import service
    from app.intent_radar.permissions import context
    service.get(c,'monitors',str(key));org=context(c).organization_id
    rows=c.execute('SELECT d.id,d.created_at,r.provider,r.status,r.result_json FROM intent_discoveries d LEFT JOIN intent_source_runs r ON r.discovery_id=d.id AND r.organization_id=d.organization_id WHERE d.organization_id=? AND d.monitor_id=? ORDER BY d.created_at DESC LIMIT 50',(org,str(key))).fetchall()
    return {'items':[{**dict(r),'result':json.loads(r['result_json'] or '{}')} for r in rows]}

@router.get('/intent-radar/opportunities',dependencies=[Depends(lambda:require('intent:read'))])
def intent_opportunities(status:str=Query('',max_length=30),page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    from app.intent_radar import service
    return service.listing(c,'opportunities',page=page,size=page_size,status=status)

@router.get('/intent-radar/icps',dependencies=[Depends(lambda:require('intent:read'))])
def intent_icps(page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.intent_radar.permissions import context
    context(c)
    from app.icp.service import listing
    return listing(c,page)

@router.get('/intent-radar/growth/overview')
def growth_overview(grant=Depends(lambda:require('intent:read')),c=Depends(get_db,scope='function')):
    from app.growth_intelligence import analytics,models
    return analytics.overview(c,models.Scope())

@router.get('/intent-radar/growth/research/{key}')
def growth_research(key:UUID,grant=Depends(lambda:require('intent:read')),c=Depends(get_db,scope='function')):
    from app.growth_intelligence.service import detail
    return detail(c,str(key))

@router.get('/intent-radar/growth/themes')
def growth_themes(search:str=Query('',max_length=120),page:int=Query(1,ge=1,le=10000),grant=Depends(lambda:require('intent:read')),c=Depends(get_db,scope='function')):
    from app.growth_intelligence.service import themes
    return themes(c,search=search,page=page,size=20)

def scope(value):
    def checked():return require(value)
    return Depends(checked)
class CompanyRecord(BaseModel):
    id:int
    name:str
    website:str|None=None
    country:str|None=None
    city:str|None=None
    industry:str
    processing_status:str|None=None
    information:dict=Field(default_factory=dict)
class CompanyPage(BaseModel):
    items:list[CompanyRecord]
    page:int
    page_size:int
    has_more:bool
class ContactRecord(BaseModel):
    id:str
    prospect_id:str
    name:str
    company_name:str|None=None
    business_id:int|None=None
    role:str|None=None
    department:str|None=None
    seniority:str|None=None
    job_function:str|None=None
    profile_url:str|None=None
    work_email:str|None=None
    phone:str|None=None
    source_url:str|None=None
    confidence:str|None=None
    discovery_state:str
    verification_state:str
    recipient_delivery_verified:bool
    evidence:dict
    checked_at:str|None=None
    archived_at:str|None=None
class ContactPage(BaseModel):
    items:list[ContactRecord]
    total:int
    page:int
    page_size:int
class ListRecord(BaseModel):
    id:str
    name:str
    description:str|None=None
    revision:int
    archived_at:str|None=None
    member_count:int=0
    contact_count:int=0
class ListPage(BaseModel):
    items:list[ListRecord]
    total:int
    page:int
    page_size:int
class JobRecord(BaseModel):
    id:str
    kind:str
    status:str
    created_at:str
    updated_at:str
    completed_at:str|None=None
    error_code:str|None=None
    attempts:int
    counts:dict[str,int]
    total:int
    page:int
    page_size:int
    items:list[dict]
    usage:dict

class ListCreate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=1,max_length=100)
    description:str=Field('',max_length=1000)

@router.get('/companies',response_model=CompanyPage,dependencies=[scope('companies:read')])
def companies(search:str=Query('',max_length=200),country:str=Query('',max_length=100),industry:str=Query('',max_length=100),page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    result=tools.read(c,'search_companies',{'search':search,'country':country,'industry':industry,'page':page})
    result['items']=[{**item,'industry':item['vertical']} for item in result['items']]
    return result
@router.get('/companies/{business_id}',response_model=CompanyRecord,dependencies=[scope('companies:read')])
def company(business_id:int,c=Depends(get_db,scope='function')):
    from app.people.service import company as parent
    from app.database.repositories import BusinessRepository
    import json
    owned=parent(c,business_id);b=BusinessRepository(c).get_by_id(business_id)
    # Company permission does not implicitly expose professional contact records.
    return {'id':b.id,'name':b.name,'website':b.website,'country':b.country,'city':b.city,'industry':b.vertical,'information':json.loads(owned['source_tags_json'] or '{}').get('company_intelligence',{})}
@router.get('/contacts',response_model=ContactPage,dependencies=[scope('contacts:read')])
def contacts(search:str=Query('',max_length=200),business_id:int|None=Query(None,ge=1),job_role:str=Query('',max_length=150),page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    from app.people.service import listing
    return listing(c,search,business_id,job_role,page=page,page_size=page_size)
@router.get('/contacts/{key}',response_model=ContactRecord,dependencies=[scope('contacts:read')])
def contact(key:UUID,c=Depends(get_db,scope='function')):
    from app.people.service import get
    return get(c,str(key))
@router.get('/icps',dependencies=[scope('icps:read')])
def icps(page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.icp.service import listing
    return listing(c,page)
@router.get('/companies/{business_id}/icp-fit/{profile_id}',dependencies=[scope('companies:read'),scope('icps:read')])
def fit(business_id:int,profile_id:UUID,c=Depends(get_db,scope='function')):
    from app.intelligence.qualification import match
    return match(c,business_id,profile_id)
@router.get('/lists',response_model=ListPage,dependencies=[scope('lists:read')])
def lists(page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.sales.collections import listing
    return listing(c,page=page)
@router.get('/lists/{key}',dependencies=[scope('lists:read')])
def get_list(key:UUID,page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.sales.collections import detail
    require('companies:read');require('contacts:read')
    return detail(c,str(key),page)
@router.post('/lists',status_code=201,response_model=ListRecord,dependencies=[scope('lists:write')])
def create_list(body:ListCreate,idempotency_key:UUID=Header(alias='Idempotency-Key'),c=Depends(get_db,scope='function')):
    from app.sales.collections import Named,save
    return save(c,Named(**body.model_dump(),request_id=idempotency_key))
@router.get('/tasks',dependencies=[scope('tasks:read')])
def tasks(status:Literal['','OPEN','COMPLETED','CANCELED']='OPEN',page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.sales.tasks import listing
    require('companies:read');return listing(c,status=status,page=page)
class Enrich(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['COMPANY_ENRICH','CONTACT_DISCOVER','CONTACT_ENRICH','CONTACT_VERIFY']
    resource_ids:list[str]=Field(min_length=1,max_length=100)
@router.post('/enrichment/jobs',status_code=202,response_model=JobRecord,dependencies=[scope('enrichment:write')])
async def enrich(body:Enrich,idempotency_key:UUID=Header(alias='Idempotency-Key'),c=Depends(get_db,scope='function')):
    require('companies:read' if body.kind in ('COMPANY_ENRICH','CONTACT_DISCOVER') else 'contacts:read')
    from app.intelligence.jobs import Start,create,detail
    from app.intelligence.dispatch import launch
    job=create(c,Start(**body.model_dump(),request_id=idempotency_key));c.commit();await launch(job['id']);return detail(c,job['id'])
@router.get('/enrichment/jobs/{key}',response_model=JobRecord,dependencies=[scope('enrichment:write')])
def enrichment_job(key:UUID,page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.intelligence.jobs import detail
    result=detail(c,str(key),page)
    if result['kind'] in ('ASSISTANT_TURN','COMPANY_SUMMARIZE'):raise HTTPException(404,'Job is not available through this API scope.')
    require('companies:read' if result['kind'] in ('COMPANY_ENRICH','CONTACT_DISCOVER') else 'contacts:read');return result
@router.get('/campaigns',dependencies=[scope('campaigns:read')])
def campaigns(c=Depends(get_db,scope='function')):return tools.read(c,'campaigns',{})

@router.get('/openapi.json',include_in_schema=False)
def openapi_document():
    from fastapi.openapi.utils import get_openapi
    from app.config.settings import get_settings
    available=get_settings().lead_engine_available
    routes=router.routes if available else [route for route in router.routes if route.path.startswith('/v1/intent-radar/')]
    document=get_openapi(title='PlaneByte Lead Engine API' if available else 'PlaneByte Intent Radar API',version='1.0.0',routes=routes)
    document.setdefault('components',{}).setdefault('securitySchemes',{})['WorkspaceKey']={'type':'http','scheme':'bearer','bearerFormat':'Scoped API key'}
    document['servers']=[{'url':'/api','description':'Same-origin API base'}]
    for path in document['paths'].values():
        for operation in path.values():
            if isinstance(operation,dict):operation['security']=[{'WorkspaceKey':[]}]
    return document

@router.get('/searches',dependencies=[scope('searches:read')])
def saved_searches(page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    from app.prospecting.searches import list_searches
    return list_searches(c,page=page)
class SearchCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=120)
    configuration:dict
@router.post('/searches',status_code=201,dependencies=[scope('searches:write')])
def save_search(body:SearchCreate,idempotency_key:UUID=Header(alias='Idempotency-Key'),c=Depends(get_db,scope='function')):
    from app.prospecting.searches import SaveSearch,save
    return save(c,SaveSearch(**body.model_dump(),request_id=idempotency_key))
