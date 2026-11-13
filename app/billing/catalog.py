"""One server catalog. Defaults are internal sandbox fixtures, NOT sale prices."""
import json,re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.config.settings import get_settings

DIMENSIONS=('searches','ai_calls','ai_tokens','monitor_executions','opportunities','api_requests')
class Allowances(BaseModel):
    model_config=ConfigDict(extra='forbid')
    searches:int=Field(20,ge=0,le=100000)
    ai_calls:int=Field(10,ge=0,le=100000)
    ai_tokens:int=Field(100000,ge=0,le=100000000)
    monitors:int=Field(3,ge=0,le=100)
    monitor_executions:int=Field(30,ge=0,le=100000)
    opportunities:int=Field(100,ge=0,le=100000)
    team_members:int=Field(1,ge=1,le=10000)
    api_requests:int=Field(1000,ge=0,le=10000000)
class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    code:Literal['starter','growth','scale','enterprise']
    name:str=Field(min_length=2,max_length=80)
    product:Literal['INTENT_RADAR']='INTENT_RADAR'
    mode:Literal['test']='test'
    internal_test_only:Literal[True]=True
    amount:int|None=Field(None,ge=100,le=1000000)
    currency:Literal['INR']='INR'
    period:Literal['monthly','yearly']='monthly'
    interval:int=Field(1,ge=1,le=12)
    total_count:int=Field(12,ge=1,le=24)
    provider_plan_id:str|None=Field(None,pattern=r'^plan_[A-Za-z0-9]{1,80}$')
    limits:Allowances=Field(default_factory=Allowances)
    @model_validator(mode='after')
    def custom(self):
        if self.code=='enterprise' and (self.amount is not None or self.provider_plan_id):raise ValueError('Custom plans require a separate approved agreement; no checkout.')
        return self

def plans(c=None):
    s=get_settings()
    if s.billing_catalog_json:
        raw=json.loads(s.billing_catalog_json)
        if not isinstance(raw,list) or len(raw)!=4:raise ValueError('Exactly four catalog entries are required.')
    else:
        raw=[{'code':code,'name':name,'amount':amount,'limits':{'searches':searches,'monitors':monitors,'team_members':seats}} for code,name,amount,searches,monitors,seats in [('starter','Starter — internal test',10000,20,3,1),('growth','Growth — internal test',20000,40,5,3),('scale','Scale — internal test',30000,60,10,5),('enterprise','Enterprise / custom',None,0,0,1)]]
    result={}
    for value in raw:
        item=Plan.model_validate(value)
        configured=getattr(s,'razorpay_test_plan_id_'+item.code,'') if item.code!='enterprise' else ''
        if not configured and c is not None:
            row=c.execute("SELECT provider_plan_id FROM billing_plan_mappings WHERE mode='test' AND code=?",(item.code,)).fetchone()
            configured=row[0] if row else ''
        if configured:item=item.model_copy(update={'provider_plan_id':configured})
        item=Plan.model_validate(item.model_dump())
        if item.code in result:raise ValueError('Duplicate plan code.')
        result[item.code]=item
    if set(result)!= {'starter','growth','scale','enterprise'}:raise ValueError('Incomplete plan catalog.')
    ids=[p.provider_plan_id for p in result.values() if p.provider_plan_id]
    if len(set(ids))!=len(ids):raise ValueError('Provider plan mappings must be distinct.')
    return result

def plan(code,c=None):
    from fastapi import HTTPException
    item=plans(c).get(code)
    if not item:raise HTTPException(422,'Choose a supported Intent Radar plan.')
    return item

def handoff(product,code):
    from fastapi import HTTPException
    if product!='intent-radar':raise HTTPException(422,'Only Intent Radar plan selection is supported.')
    p=plan(code)
    return {'product':'intent-radar','plan':p.code,'destination':'/billing?plan='+p.code,'checkout_enabled':False,'requires_authenticated_workspace':True,'commercial_price_approved':False}
