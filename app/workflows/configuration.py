"""Owner-approved operational copy and reuse policy; credentials stay in env."""
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.database.prospects import now

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class ReuseWindows(Strict):
    contacts:int=Field(7,ge=1,le=90)
    crawl:int=Field(7,ge=1,le=90)
    website:int=Field(7,ge=1,le=90)
    seo:int=Field(7,ge=1,le=90)
    security:int=Field(7,ge=1,le=90)
    social:int=Field(7,ge=1,le=90)
    lighthouse:int=Field(14,ge=1,le=90)
class Sender(Strict):
    display_name:str=Field('PlaneByte',min_length=1,max_length=100)
    human_sender_name:str=Field('',max_length=100)
    sender_role:str=Field('',max_length=120)
    company:Literal['PlaneByte']='PlaneByte'
    website:str=Field('https://planebyte.com',max_length=500)
    contact_email:str=Field('contact@planebyte.com',max_length=254)
    @model_validator(mode='after')
    def safe(self):
        from app.mail.service import header,address
        from app.reports.data import public_url
        for v in (self.display_name,self.human_sender_name,self.sender_role):header(v)
        address(self.contact_email)
        if not public_url(self.website):raise ValueError('Use a public company website URL.')
        return self
class ReportCopy(Strict):
    company_description:str=Field('',max_length=700)
    why_planebyte:list[str]=Field(default_factory=list,max_length=3)
    cta:str=Field("If this is already on your roadmap, reply here and I can send over a suggested priority order and rough implementation scope.",min_length=20,max_length=350)
    signature_tagline:str=Field('Software Engineering · SEO · Security',max_length=150)
    service_labels:dict[Literal['WEBSITE','SEO','SECURITY'],str]=Field(default_factory=dict)
    include_seo:bool=True
    include_security:bool=True
    include_validation:bool=True
    @model_validator(mode='after')
    def concise(self):
        self.why_planebyte=[v.strip() for v in self.why_planebyte if v.strip()]
        self.service_labels={k:v.strip() for k,v in self.service_labels.items() if v.strip()}
        if 'reply' not in self.cta.casefold():raise ValueError('The CTA must invite a reply.')
        if any(len(v)>500 for v in self.why_planebyte) or any(len(v)>120 for v in self.service_labels.values()):raise ValueError('Keep approved copy concise.')
        return self
class Pitch(Strict):
    enabled:bool=True
    minimum_score:int=Field(40,ge=40,le=100)
    minimum_findings:int=Field(2,ge=2,le=5)
    required_evidence:list[str]=Field(default_factory=list,max_length=10)
    @model_validator(mode='after')
    def codes(self):
        from app.reports.copy import FINDING_COPY
        if any(code not in FINDING_COPY for code in self.required_evidence):raise ValueError('Choose supported evidence codes.')
        return self
class FoundationSettings(Strict):
    reuse_windows:ReuseWindows=Field(default_factory=ReuseWindows)
    sender:Sender=Field(default_factory=Sender)
    report:ReportCopy=Field(default_factory=ReportCopy)
    pitches:dict[Literal['WEBSITE','SEO','SECURITY'],Pitch]=Field(default_factory=lambda:{k:Pitch() for k in ('WEBSITE','SEO','SECURITY')})

def load(c,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    if organization:
        from app.api.organization import workspace_settings
        saved=(workspace_settings(c,organization) or {}).get('foundation')
    else:saved=None
    if saved:return FoundationSettings.model_validate(saved)
    from app.mail.config import mail_settings
    s=mail_settings()
    return FoundationSettings(sender=Sender(display_name=s.from_name,human_sender_name=s.outreach_sender_name,sender_role=s.outreach_sender_role,company='PlaneByte',website=s.website,contact_email='contact@planebyte.com'))

def save(c,value,actor,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    from app.api.organization import workspace_settings,save_workspace_settings
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944520)')
    data=workspace_settings(c,organization) or {}
    data['foundation']=value.model_dump()
    save_workspace_settings(c,organization,data,actor)
