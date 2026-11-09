"""One bounded tool registry; models cannot choose SQL, URLs or transport code."""
import json
from uuid import UUID
from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field
from fastapi import HTTPException
from app.people import service as people
from app.platform.context import current

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class CompanySearch(Strict):
    search:str=Field('',max_length=200)
    country:str=Field('',max_length=100)
    industry:str=Field('',max_length=100)
    page:int=Field(1,ge=1,le=10000)
class CompanyID(Strict):business_id:int=Field(ge=1,le=9223372036854775807)
class ContactSearch(Strict):
    search:str=Field('',max_length=200)
    business_id:int|None=Field(None,ge=1,le=9223372036854775807)
class Fit(CompanyID):
    profile_id:UUID|None=None
    contact_id:UUID|None=None
class Empty(Strict):pass
class HelpSearch(Strict):query:str=Field('',max_length=200)
class Enrich(Strict):
    kind:Literal['COMPANY_ENRICH','CONTACT_DISCOVER']='COMPANY_ENRICH'
    business_ids:list[Annotated[int,Field(ge=1,le=9223372036854775807)]]=Field(min_length=1,max_length=10)

READ={'search_companies':CompanySearch,'company_details':CompanyID,'search_contacts':ContactSearch,'match_icp':Fit,'list_icps':Empty,'list_lists':Empty,'campaigns':Empty,'product_help':HelpSearch}

def read(c,name,arguments):
    if name not in READ:raise HTTPException(422,'Choose an available assistant read tool.')
    args=READ[name].model_validate(arguments);org=people.ctx(c).organization_id
    if name=='product_help':
        from app.platform.product_help import search
        return {'items':search(args.query),'support_email':'contact@planebyte.com','live_chat_available':False}
    if name=='search_companies':
        where=['r.organization_id=?'];params=[org]
        for field,value in [('name',args.search),('country',args.country),('vertical',args.industry)]:
            if value:where.append('LOWER(b.'+field+') LIKE ?');params.append('%'+value.casefold()+'%')
        rows=c.execute('SELECT b.id,b.name,b.website,b.country,b.city,b.vertical,b.processing_status FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE '+' AND '.join(where)+' AND b.id=(SELECT MAX(b2.id) FROM businesses b2 JOIN pipeline_runs r2 ON r2.id=b2.run_id WHERE b2.prospect_id=b.prospect_id AND r2.organization_id=?) ORDER BY b.id DESC LIMIT 20 OFFSET ?',[*params,org,(args.page-1)*20]).fetchall()
        return {'items':[dict(row) for row in rows],'page':args.page,'page_size':20,'has_more':len(rows)==20}
    if name=='company_details':
        parent=people.company(c,args.business_id)
        from app.database.repositories import BusinessRepository
        b=BusinessRepository(c).get_by_id(args.business_id)
        return {'id':b.id,'name':b.name,'website':b.website,'country':b.country,'city':b.city,'industry':b.vertical,'information':json.loads(parent['source_tags_json'] or '{}').get('company_intelligence',{}),'people':people.listing(c,business_id=b.id,page_size=10)['items']}
    if name=='search_contacts':return people.listing(c,search=args.search,business_id=args.business_id,page_size=20)
    if name=='match_icp':
        from app.intelligence.qualification import match
        return match(c,args.business_id,args.profile_id,str(args.contact_id) if args.contact_id else None)
    if name=='list_icps':
        from app.icp.service import listing
        return listing(c)
    if name=='list_lists':return {'items':[dict(row) for row in c.execute('SELECT id,name,description FROM lead_lists WHERE organization_id=? AND archived_at IS NULL ORDER BY name LIMIT 25',(org,)).fetchall()]}
    return {'items':[dict(row) for row in c.execute('SELECT id,name,kind,status,created_at FROM workflow_runs WHERE organization_id=? ORDER BY created_at DESC LIMIT 20',(org,)).fetchall()]}


def validate_action(c,name,arguments):
    people.ctx(c,True)
    if name=='save_search':
        from app.prospecting.searches import SaveSearch,configuration
        body=SaveSearch.model_validate(arguments);configuration(c,body.configuration)
    elif name=='enrich_companies':
        body=Enrich.model_validate(arguments)
        for key in body.business_ids:people.company(c,key)
    elif name=='create_list':
        from app.sales.collections import Named
        body=Named.model_validate(arguments)
    elif name=='create_task':
        from app.sales.tasks import Task,validate
        body=Task.model_validate(arguments);validate(c,body)
    else:raise HTTPException(422,'This assistant action is unavailable. No messages or scans can be started by the assistant.')
    return body.model_dump(mode='json')


def apply(c,key,kind,payload):
    payload=validate_action(c,kind,payload)
    if kind=='save_search':
        from app.prospecting.searches import SaveSearch,save
        return {'search':save(c,SaveSearch.model_validate(payload))}
    if kind=='create_list':
        from app.sales.collections import Named,save
        return {'list':save(c,Named.model_validate(payload))}
    if kind=='create_task':
        from app.sales.tasks import Task,create
        return {'task':create(c,Task.model_validate(payload))}
    from app.intelligence.jobs import Start,create
    import uuid
    return {'job':create(c,Start(kind=payload['kind'],resource_ids=[str(key) for key in payload['business_ids']],request_id=uuid.uuid5(uuid.NAMESPACE_URL,'assistant-action:'+key)))}
