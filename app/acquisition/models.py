from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field,model_validator,field_validator
from app.config.locations import country
Source=Literal['OVERTURE','FIRECRAWL','FILE_IMPORT','GOOGLE_SHEETS']
Vertical=Annotated[str,Field(min_length=2,max_length=100,pattern=r'^[^\x00-\x1f]+$')]
FIELDS=('company_name','website','email','phone','city','country','vertical','contact_name','address','region')
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,strict=True)
from app.prospecting.criteria import SearchCriteria
class SearchIntent(Strict):
    search_criteria:SearchCriteria=Field(default_factory=SearchCriteria)
    targetQualifiedLeads:int=Field(50,ge=1,le=1000)
    verticals:list[Vertical]=Field(min_length=1,max_length=4)
    countries:list[str]=Field(min_length=1,max_length=5)
    cities:list[str]=Field(default_factory=list,max_length=10)
    businessSizes:list[Literal['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL']]=Field(default_factory=lambda:['LOCAL','SMALL_GROUP','MID_MARKET'],min_length=1,max_length=4)
    opportunities:list[Literal['WEBSITE','SEO','SECURITY']]=Field(default_factory=list,max_length=3,deprecated=True)
    contactRequired:Literal[True]=True
    source:Literal['FIRECRAWL']='FIRECRAWL'
    queries:list[str]=Field(min_length=1,max_length=6)
    @field_validator('countries')
    @classmethod
    def known_countries(cls,values):return list(dict.fromkeys(country(v).name for v in values))
    @field_validator('queries','cities')
    @classmethod
    def bounded_text(cls,values):
        if any(not v.strip() or len(v)>300 or any(ord(c)<32 for c in v) for v in values):raise ValueError('Use bounded plain-text locations and queries.')
        return list(dict.fromkeys(v.strip() for v in values))
class Budgets(Strict):
    max_credits:int|None=Field(None,ge=1,le=10000)
    max_searches:int=Field(6,ge=1,le=20)
    max_scraped_pages:int=Field(40,ge=1,le=200)
    max_crawl_pages:int=Field(0,ge=0,le=5)
    max_runtime_seconds:int=Field(1200,ge=60,le=3600)
    max_candidates:int=Field(200,ge=1,le=1000)
class ProcessingOptions(Strict):
    find_missing_contacts:bool=False
    qualification_mode:Literal['CONTACTABLE_ONLY','ANALYZED','STRICT']='CONTACTABLE_ONLY'
    analyze_websites:bool=False
    analyze_seo:bool=False
    analyze_security:bool=False
    lighthouse:bool=False
    default_country:str='United Kingdom'
    default_city:str=Field('',max_length=100)
    default_vertical:Vertical='hospitality'
    @field_validator('default_country')
    @classmethod
    def known_country(cls,v):return country(v).name
    @model_validator(mode='before')
    @classmethod
    def historical(cls,v):
        if isinstance(v,dict) and 'qualification_mode' not in v and any(v.get(k) for k in ('analyze_websites','analyze_seo','analyze_security')):v={**v,'qualification_mode':'ANALYZED'}
        return v
    @model_validator(mode='after')
    def analysis(self):
        self.analyze_websites=self.analyze_seo=self.analyze_security=self.lighthouse=False

        return self
class ColumnMapping(Strict):
    company_name:str|None=None
    website:str|None=None
    email:str|None=None
    phone:str|None=None
    city:str|None=None
    country:str|None=None
    vertical:str|None=None
    contact_name:str|None=None
    address:str|None=None
    region:str|None=None
    def validate_headers(self,headers):
        if not self.company_name:raise ValueError('Map a company-name column before importing.')
        values=[v for v in self.model_dump().values() if v is not None]
        if any(v not in headers for v in values):raise ValueError('Mapping refers to a column outside the selected sheet.')
        if len(values)!=len(set(values)):raise ValueError('Map each source column to one LeadEngine field.')
        return self
