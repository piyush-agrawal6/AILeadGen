"""Explicit discovery filters with honest post-discovery/unknown evaluation."""
import re
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
Term=Annotated[str,Field(min_length=1,max_length=160)]
class SearchCriteria(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    keywords:list[Term]=Field(default_factory=list,max_length=20)
    exclude_terms:list[Term]=Field(default_factory=list,max_length=20)
    categories:list[Term]=Field(default_factory=list,max_length=20)
    regions:list[Term]=Field(default_factory=list,max_length=20)
    company_names:list[Term]=Field(default_factory=list,max_length=20)
    domains:list[Term]=Field(default_factory=list,max_length=20)
    company_sizes:list[Literal['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL','ENTERPRISE']]=Field(default_factory=list,max_length=5)
    employee_min:int|None=Field(None,ge=0,le=10000000)
    employee_max:int|None=Field(None,ge=0,le=10000000)
    existing_companies:Literal['INCLUDE','EXCLUDE','ONLY']='INCLUDE'
    @field_validator('keywords','exclude_terms','categories','regions','company_names','domains')
    @classmethod
    def plain(cls,values):
        if any(any(ord(c)<32 for c in value) for value in values):raise ValueError('Use plain text search terms.')
        return list(dict.fromkeys(values))
    @field_validator('domains')
    @classmethod
    def domain_names(cls,values):
        from app.utils.urls import extract_domain,sanitize_url,is_safe_url
        result=[]
        for value in values:
            url=sanitize_url(value)
            if not url or not is_safe_url(url,check_dns=False):raise ValueError('Use public company domain names.')
            result.append(extract_domain(url))
        return list(dict.fromkeys(result))
    @model_validator(mode='after')
    def ranges(self):
        if self.employee_min is not None and self.employee_max is not None and self.employee_min>self.employee_max:raise ValueError('Minimum employees must not exceed maximum employees.')
        return self

def normalized(value):return re.sub(r'[^\w]+',' ',str(value).casefold()).strip()

def evaluate(b,facts,criteria,*,existing=False):
    """These are observed matches, not a fabricated company-fit or revenue score."""
    criteria=SearchCriteria.model_validate(criteria or {});checks=[]
    text=normalized(' '.join([b.name,b.source_category or '',b.subcategory or '',*[p.get('excerpt','') for p in facts.get('pages',[])]]))
    for key,actual in [('keywords',text),('exclude_terms',text),('categories',normalized(' '.join([b.source_category or '',b.subcategory or '']))),('regions',normalized(b.state or '')),('company_names',normalized(b.name)),('domains',b.domain or '')]:
        expected=getattr(criteria,key)
        if not expected:continue
        matches=any((actual==value if key=='domains' else normalized(value) in actual) for value in expected)
        status=('EXCLUDED' if matches else 'MATCH') if key=='exclude_terms' else 'UNKNOWN' if not actual else 'MATCH' if matches else 'NOT_OBSERVED'
        checks.append({'field':key,'status':status,'expected':expected,'evaluation':'POST_DISCOVERY_PUBLIC_EVIDENCE'})
    for key in ('company_sizes','employee_min','employee_max'):
        if getattr(criteria,key) not in (None,[]):checks.append({'field':key,'status':'UNKNOWN','evaluation':'REQUIRES_RELIABLE_COMPANY_EVIDENCE'})
    if criteria.existing_companies!='INCLUDE':checks.append({'field':'existing_companies','status':'MATCH' if existing==(criteria.existing_companies=='ONLY') else 'EXCLUDED','evaluation':'WORKSPACE_HISTORY'})
    status='EXCLUDED' if any(x['status']=='EXCLUDED' for x in checks) else 'NEEDS_REVIEW' if any(x['status'] in ('UNKNOWN','NOT_OBSERVED') for x in checks) else 'MATCH'
    return {'status':status,'criteria':checks}

def capabilities():
    return {'discovery_filters':['countries','cities','industry'],'post_discovery_filters':['keywords','exclude_terms','categories','regions','company_names','domains','existing_companies'],'evidence_required':['company_sizes','employee_min','employee_max'],'countries':[{'code':code,'availability':'SOURCE_DEPENDENT','live_coverage_verified':False} for code in ('US','GB','CA','AU','DE','FR','IN')],'coverage_note':'Public source coverage varies by category and location. These are supported geography inputs, not verified live yield guarantees.'}
