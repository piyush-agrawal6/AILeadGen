"""Small module registry and fail-closed legacy availability policy.

Availability is not a purchased entitlement. Billing and unavailable modules are
never represented as active subscriptions or working product capabilities.
"""
from dataclasses import dataclass
from typing import Literal
from fastapi import HTTPException
from app.config.settings import get_settings

@dataclass(frozen=True)
class Module:
    id:str
    name:str
    version:str
    lifecycle:Literal['AVAILABLE','DISABLED','PLANNED']
    routes:tuple[str,...]
    permissions:tuple[str,...]
    usage_dimensions:tuple[str,...]=()

MODULES={m.id:m for m in (
  Module('lead_engine','Lead Engine','1','AVAILABLE',('/api/acquisition','/api/workflow'),('read','operate'),('discovery_runs','companies')),
  Module('intent_radar','Intent Radar','1','DISABLED',('/api/intent-radar',),('read','operate'),('intent_searches','intent_signals')),
 Module('sales','Sales workspace','1','AVAILABLE',('/api/sales','/api/email'),('read','operate','send'),('emails_sent',)),
 Module('legacy_experiment','Internal experiment archive','1','DISABLED',('/api/experiments','/api/email/intro-analytics'),('owner',)),
 Module('ai_agent','HeySow AI Agent','1','PLANNED',(),('read','operate'),('ai_requests',)),
 Module('search_visibility','Search Visibility','1','PLANNED',(),('read','assess')),
 Module('security_assessment','Security assessments','1','DISABLED',(),('explicit_authorization',)),
)}

def legacy_enabled():
    return get_settings().heysow_internal_experiments_enabled

def require_legacy():
    if not legacy_enabled():raise HTTPException(409,'This internal experiment is archived. Use a workspace template and review the campaign recipients.')
    from app.platform.context import organization
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if organization()!=PLANEBYTE_ORGANIZATION_ID:raise HTTPException(404,'Not found.')

LEAD_ROUTES=('/api/dashboard','/api/assistant','/api/qualification','/api/deletions','/api/organization/integrations','/api/organization/developer/approvals','/api/acquisition','/api/workflow','/api/operations','/api/people','/api/discovery','/api/campaigns','/api/scans','/api/sales','/api/intelligence','/api/leads','/api/reports','/api/client-reports','/api/email','/api/automation','/api/settings','/api/markets','/api/verticals')

def lead_engine_route(path):
    shared_job=path=='/api/intelligence/jobs' or path.startswith('/api/intelligence/jobs/')
    foundation_lead=any(path==prefix or path.startswith(prefix+'/') for prefix in ('/api/foundation/repeat','/api/foundation/campaigns','/api/foundation/contacts','/api/foundation/history','/api/foundation/efficiency','/api/foundation/market-groups','/api/foundation/quality','/api/foundation/reviews','/api/foundation/duplicates','/api/foundation/usage','/api/foundation/cache'))
    return not shared_job and (foundation_lead or any(path==prefix or path.startswith(prefix+'/') for prefix in LEAD_ROUTES))

def guard_route(path,*,organization_id,role,method='GET'):
    if not get_settings().lead_engine_available and lead_engine_route(path):
        raise HTTPException(404,'This product is unavailable.')
    if path.startswith('/api/intent-radar/growth'):
        if not get_settings().intent_radar_growth_enabled:raise HTTPException(404,'Growth Intelligence is unavailable.')
    if path=='/api/intent-radar' or path.startswith('/api/intent-radar/'):
        from app.database.connection import db_session
        from app.intent_radar.permissions import availability
        with db_session() as c:
            if not role or not availability(c,organization_id)['enabled']:raise HTTPException(404,'Intent Radar is unavailable.')
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    internal=('/api/automation/controls','/api/automation/markets','/api/foundation/emergency',
              '/api/foundation/health','/api/foundation/settings','/api/system',
              '/api/acquisition/providers','/api/acquisition/sheets')
    if any(path==prefix or path.startswith(prefix+'/') for prefix in internal):
        if organization_id!=PLANEBYTE_ORGANIZATION_ID:
            raise HTTPException(403,'This platform operation is available only to the internal workspace.')
    legacy=any(path==p or path.startswith(p+'/') for p in MODULES['legacy_experiment'].routes)
    if not legacy:return
    if not legacy_enabled() or organization_id!=PLANEBYTE_ORGANIZATION_ID:raise HTTPException(404,'Not found.')
    if role!='OWNER':raise HTTPException(403,'This archive requires the workspace owner.')
    if method not in ('GET','HEAD'):raise HTTPException(409,'This experiment is a read-only archive; no new jobs or messages can be started.')


def guard_product_route(c,path,organization_id):
    """Separate product enrollment from account/setup/legacy availability gates."""
    shared_job=path=='/api/intelligence/jobs' or path.startswith('/api/intelligence/jobs/')
    if not shared_job and lead_engine_route(path):
        from app.api.organization import products
        if not organization_id or not products(c,organization_id).get('LEADGEN'):raise HTTPException(404,'Lead Engine is unavailable for this workspace.')
