from uuid import UUID
from fastapi import APIRouter,Depends,Query
from app.api.dependencies import get_db
from app.intelligence import qualification
router=APIRouter(prefix='/qualification',tags=['Evidence-based ICP matching'])
@router.get('/companies/{business_id}')
def match(business_id:int,profile_id:UUID|None=None,contact_id:UUID|None=None,c=Depends(get_db,scope='function')):
    return qualification.match(c,business_id,profile_id,str(contact_id) if contact_id else None)
@router.get('/recommendations/{profile_id}')
def recommendations(profile_id:UUID,page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    return qualification.recommendations(c,profile_id,page,page_size)

@router.get('/companies/{business_id}/summary')
def summary(business_id:int,c=Depends(get_db,scope='function')):
    import json
    from app.people.service import company
    return json.loads(company(c,business_id)['source_tags_json'] or '{}').get('company_summary',{'status':'NOT_PREPARED'})
