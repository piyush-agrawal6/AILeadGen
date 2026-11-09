"""Freeze qualification defaults only when creating a new Maps execution."""
import json
DEFAULTS={'qualification_mode':'BALANCED','qualified_score_threshold':35,'preliminary_opportunity_threshold':10,'deep_audit_budget':0,'lighthouse_budget':0,'max_candidates':300,'max_runtime_seconds':1200,'analysis_reuse_days':7,'email_enrichment_reuse_days':7}

def new_scan_settings(c,options=None):
    options=dict(options or {})
    from app.api.organization import workspace_settings
    from app.platform.context import organization
    saved=(workspace_settings(c,organization()) or {}).get('manual_defaults',{})
    defaults={key:saved.get(key,value) for key,value in DEFAULTS.items()}
    result={**defaults,**options,'qualification_flow_version':1,'source_type':'OVERTURE','processing_policy':'DISCOVERY_QUALIFIED'}
    if 'qualification_mode' not in options:
        from app.config.settings import get_settings
        result['qualification_mode']=get_settings().lead_qualification_mode
    if result['qualification_mode']=='CONTACTABLE_ONLY':
        from app.qualification.contactable import defaults as contactable_defaults
        result.update(contactable_defaults());result.update(lighthouse_enabled=False,social_enrichment_enabled=False,social_activity_enabled=False,exclude_chains=False)
    result.setdefault('opportunities',[])
    result['raw_budget']=min(result.get('raw_budget') or result['max_candidates'],result['max_candidates'])
    result.setdefault('reuse_windows',{key:result['analysis_reuse_days'] for key in ('crawl','website','seo','security')})
    result['reuse_windows']={**result['reuse_windows'],'contacts':result['email_enrichment_reuse_days']}
    from app.prospecting.policy import configuration
    return configuration(result)
