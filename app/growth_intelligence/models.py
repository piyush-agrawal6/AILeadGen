from typing import Literal,Annotated
from uuid import UUID,uuid4
from pydantic import BaseModel,ConfigDict,Field

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Scope(Strict):
    days:Literal[0,7,30,90]=0
    sources:list[Annotated[str,Field(min_length=1,max_length=100)]]=Field(default_factory=list,max_length=4)
    search:str=Field('',max_length=160)
    min_score:int=Field(0,ge=0,le=100)
    language:Literal['any','en','es','fr','de','pt','hi','ja']='any'
    theme_ids:list[UUID]=Field(default_factory=list,max_length=5)
    competitor_id:UUID|None=None
    icp_id:UUID|None=None

class AssistantContext(Strict):
    thread_id:UUID|None=None
    page:Literal['overview','discover','opportunities','growth','monitors','integrations','billing','settings','library']='overview'
    signal_ids:list[UUID]=Field(default_factory=list,max_length=5)

class Start(Strict):
    kind:Literal['THEMES','RESEARCH','REPORT']='THEMES'
    report_type:Literal['Market overview','Emerging demand','Competitor alternatives','Intent summary','Opportunity shortlist','Watchlist activity','Market comparison']='Market overview'
    title:str=Field('Market research',min_length=1,max_length=120)
    question:str=Field('',max_length=1500)
    scope:Scope=Field(default_factory=Scope)
    request_id:UUID=Field(default_factory=uuid4)
    assistant:AssistantContext|None=None

class Citation(Strict):
    signal_id:UUID
    quote:str=Field(min_length=3,max_length=500)

class Theme(Strict):
    name:str=Field(min_length=3,max_length=100)
    description:str=Field(min_length=3,max_length=500)
    citations:list[Citation]=Field(min_length=1,max_length=12)

class Finding(Strict):
    section:Literal['Customer problem','Comparison','Intent evidence','Opportunity','Limitation','Next research']
    interpretation:str=Field(min_length=3,max_length=500)
    citations:list[Citation]=Field(min_length=1,max_length=5)

class Interpretation(Strict):
    themes:list[Theme]=Field(default_factory=list,max_length=8)
    findings:list[Finding]=Field(default_factory=list,max_length=10)
    limitations:list[Annotated[str,Field(min_length=3,max_length=300)]]=Field(default_factory=list,max_length=5)

class ThemeUpdate(Strict):
    revision:int=Field(ge=1)
    saved:bool=False
    status:Literal['Active','Archived']='Active'

class Save(Strict):
    revision:int=Field(ge=1)
    saved:bool=True

class Competitor(Strict):
    name:str=Field(min_length=2,max_length=100)
    aliases:list[Annotated[str,Field(min_length=2,max_length=100)]]=Field(default_factory=list,max_length=5)
    context:str=Field('',max_length=500)
    request_id:UUID=Field(default_factory=uuid4)
    revision:int|None=Field(None,ge=1)
    archived:bool=False

class Watchlist(Strict):
    name:str=Field(min_length=2,max_length=120)
    kind:Literal['Market','Theme','Competitor','Industry','Customer problem','Topic','Product','ICP']='Market'
    resource_id:UUID|None=None
    keywords:list[Annotated[str,Field(min_length=1,max_length=100)]]=Field(min_length=1,max_length=12)
    request_id:UUID=Field(default_factory=uuid4)

class Note(Strict):
    body:str=Field(min_length=1,max_length=4000)
    revision:int|None=Field(None,ge=1)

class LinkCompany(Strict):
    business_id:int=Field(ge=1,le=9223372036854775807)
