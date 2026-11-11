from uuid import UUID
from pydantic import Field
from app.intent_radar.models import Strict
from app.intent_radar import service
class Search(Strict):
    search:str=Field('',max_length=120)
    page:int=Field(1,ge=1,le=10000)
class SignalID(Strict):id:UUID
class Empty(Strict):pass
READ={'search_intent_signals':Search,'list_intent_monitors':Empty,'get_intent_signal':SignalID,'list_intent_opportunities':Empty,'list_intent_sources':Empty,'get_intent_analysis':SignalID,'get_intent_run':SignalID}
def read(c,name,arguments):
    args=READ[name].model_validate(arguments)
    if name=='list_intent_sources':
        from app.intent_radar.providers import catalog
        return {'items':catalog(c)}
    if name=='get_intent_analysis':
        from app.intent_radar.intelligence import history
        result=history(c,str(args.id));result['items']=result['items'][:1]
        return result
    if name=='get_intent_run':
        from app.intent_radar.discovery import owned_job
        return owned_job(c,str(args.id))
    if name=='get_intent_signal':return service.get(c,'signals',str(args.id))
    if name=='search_intent_signals':return service.listing(c,'signals',page=args.page,size=20,search=args.search)
    return service.listing(c,'monitors' if name=='list_intent_monitors' else 'opportunities',size=20)
