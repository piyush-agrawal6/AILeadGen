"""Local signed-session browser fixture; no external AI, crawling, mail or payments."""
from types import SimpleNamespace
from tests.intent_only_fixture_server import app,settings,path
from app.database.connection import db_session
from app.api.organization import create_organization
from app.platform.workspaces import select_workspace
from app.platform import company_autofill as autofill
from app.icp import ai as icp_ai,builder
from app.acquisition import ai
from app.acquisition.config import AcquisitionSettings
from app.platform.onboarding_ai import Advice
settings.heysow_company_discovery_enabled=True
settings.heysow_company_ai_enabled=True
settings.heysow_icp_ai_enabled=True
config=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,AI_PRIMARY_PROVIDER='vertex')
autofill.provider_settings=lambda:config
icp_ai.provider_settings=lambda:config
async def crawl(website,active):
    active()
    if '/failure' in website:raise ValueError('Synthetic inaccessible website fixture')
    return [{'id':'S1','url':website,'text':'Synthetic Browser Engineering builds Custom applications for Software teams.'}]
autofill.collect_sources=crawl
async def structured(instruction,payload,schema,**kwargs):
    if schema is autofill.Extraction:
        quote={'source_id':'S1','quote':'Synthetic Browser Engineering builds Custom applications for Software teams.'}
        return autofill.Extraction(fields=[{'field':'name','value':'Synthetic Browser Engineering','evidence':[quote]},{'field':'description','value':quote['quote'],'evidence':[quote]},{'field':'products_services','value':[{'name':'Custom applications'}],'evidence':[quote]}])
    if schema is builder.Suggestions:
        return builder.Suggestions(candidates=[builder.Candidate(draft={'name':name,'criteria':{'company':{'industries':['Software']},'contact':{'job_titles':['CTO']},'intent':{'business_needs':['Custom applications'],'pain_points':['delivery bottlenecks'],'exclusions':['recruitment']}}},reason='Synthetic fixture recommendation based on the approved offering.',assumptions=['Suggested audience; no actual customer relationship established.']) for name in ('Product engineering teams','Software studios')])
    if schema is Advice:return Advice(answer='Review the suggested business needs before choosing an audience.',source_fields=['description'])
    raise AssertionError('Unexpected isolated onboarding provider schema')
ai.provider=lambda c=None:SimpleNamespace(structured=structured,last_provider='SYNTHETIC',last_model='SYNTHETIC-browser-fixture',last_usage={})
with db_session() as c:
    org=create_organization(c,'cofounder@leadengine.example','Synthetic onboarding company')['organization_id']
    # Explicit fixture enrollment. Production onboarding never grants a product.
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(org,))
    select_workspace(c,'cofounder@leadengine.example',org)
