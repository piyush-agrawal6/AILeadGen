from fastapi import APIRouter,Query
from app.platform.product_help import search
router=APIRouter(prefix='/help',tags=['Product help'])
@router.get('/topics')
def topics(query:str=Query('',max_length=200)):
    from app.platform.context import current
    current()
    return {'items':search(query,12),'support_email':'contact@planebyte.com'}
