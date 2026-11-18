from typing import Annotated,Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

Term=Annotated[str,Field(min_length=1,max_length=180)]
Terms=Annotated[list[Term],Field(max_length=50)]


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)

    @field_validator('*',mode='after')
    @classmethod
    def clean_terms(cls,value):
        if isinstance(value,list) and all(isinstance(item,str) for item in value):return list(dict.fromkeys(value))
        return value


class CompanyCriteria(Strict):
    industries:Terms=Field(default_factory=list)
    sub_industries:Terms=Field(default_factory=list)
    business_categories:Terms=Field(default_factory=list)
    company_sizes:Terms=Field(default_factory=list)
    employee_min:int|None=Field(None,ge=0,le=10000000)
    employee_max:int|None=Field(None,ge=0,le=10000000)
    revenue_min:float|None=Field(None,ge=0,le=1e15)
    revenue_max:float|None=Field(None,ge=0,le=1e15)
    revenue_currency:str=Field('USD',pattern=r'^[A-Z]{3}$')
    business_models:Terms=Field(default_factory=list)
    technologies:Terms=Field(default_factory=list)
    maturity:Terms=Field(default_factory=list)
    countries:Terms=Field(default_factory=list)
    regions:Terms=Field(default_factory=list)
    cities:Terms=Field(default_factory=list)
    languages:Terms=Field(default_factory=list)
    website_characteristics:Terms=Field(default_factory=list)

    @model_validator(mode='after')
    def ordered_ranges(self):
        for lower,upper in ((self.employee_min,self.employee_max),(self.revenue_min,self.revenue_max)):
            if lower is not None and upper is not None and lower>upper:raise ValueError('The minimum must not exceed the maximum.')
        return self


class ContactCriteria(Strict):
    job_titles:Terms=Field(default_factory=list)
    job_functions:Terms=Field(default_factory=list)
    seniority:Terms=Field(default_factory=list)
    departments:Terms=Field(default_factory=list)
    responsibilities:Terms=Field(default_factory=list)
    countries:Terms=Field(default_factory=list)
    professional_requirements:Terms=Field(default_factory=list)


class IntentCriteria(Strict):
    business_needs:Terms=Field(default_factory=list,description='Concrete operational or commercial needs this buyer segment is trying to solve.')
    pain_points:Terms=Field(default_factory=list,description='Specific recurring frustrations or gaps motivating this buyer to evaluate solutions.')
    buying_signals:Terms=Field(default_factory=list,description='2 to 4 concrete, observable public buying triggers and buyer-intent signals (e.g. specific questions, vendor comparisons, workflow complaints, or evaluations this buyer posts publicly).')
    growth_signals:Terms=Field(default_factory=list,description='Optional observable growth or hiring signals indicating readiness.')
    relevant_services:Terms=Field(default_factory=list)
    technology_requirements:Terms=Field(default_factory=list)
    qualification_conditions:Terms=Field(default_factory=list)
    exclusions:Terms=Field(default_factory=list,description='1 to 3 context-sensitive negative exclusion criteria (e.g. student projects, job seekers, unrelated consumer/free-only requests) to filter out noisy signals.')


class Criteria(Strict):
    weights:dict[str,Annotated[int,Field(ge=1,le=10)]]=Field(default_factory=dict,max_length=60)

    @field_validator('weights')
    @classmethod
    def valid_weights(cls,value):
        groups={'company':CompanyCriteria,'contact':ContactCriteria,'intent':IntentCriteria}
        for key in value:
            group,_,field=key.partition('.')
            if group not in groups or field not in groups[group].model_fields or field=='revenue_currency':raise ValueError('Choose a defined company, contact or intent criterion for weighting.')
        return value

    company:CompanyCriteria=Field(default_factory=CompanyCriteria)
    contact:ContactCriteria=Field(default_factory=ContactCriteria)
    intent:IntentCriteria=Field(default_factory=IntentCriteria)

    @model_validator(mode='after')
    def meaningful(self):
        company=self.company.model_dump(exclude={'revenue_currency'})
        values=[*company.values(),*self.contact.model_dump().values(),*self.intent.model_dump().values()]
        if not any(value is not None and value!=[] and value!='' for value in values):
            raise ValueError('Define at least one targeting criterion before saving.')
        return self


class ProfileFields(Strict):
    name:str=Field(min_length=2,max_length=120)
    description:str=Field('',max_length=1000)
    criteria:Criteria
    status:Literal['ACTIVE','INACTIVE','ARCHIVED']='INACTIVE'


class Create(ProfileFields):
    request_id:UUID
    ai_proposal_id:UUID|None=None


class Update(ProfileFields):
    revision:int=Field(ge=1)
    ai_proposal_id:UUID|None=None


class Profile(ProfileFields):
    generation_source:Literal['MANUAL','BUSINESS_PROFILE','AI_ASSISTED','AI_REFINED']='MANUAL'
    id:UUID
    organization_id:UUID
    revision:int
    created_at:str
    updated_at:str
    created_by:str
    updated_by:str


class ProfilePage(BaseModel):
    items:list[Profile]
    total:int
    page:int
    page_size:int
    can_edit:bool


class Duplicate(Strict):
    name:str=Field(min_length=2,max_length=120)
    request_id:UUID


class Version(BaseModel):
    revision:int
    snapshot:Profile
    changed_by:str
    created_at:str


class VersionPage(BaseModel):
    items:list[Version]
    total:int
    page:int
    page_size:int
