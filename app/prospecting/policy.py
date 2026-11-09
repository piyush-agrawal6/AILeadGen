"""One product boundary applied to current and historical discovery jobs."""
FLOW='PROSPECTING_V1'
AUDIT_FLAGS=('lighthouse_enabled','lighthouse','analyze_websites','analyze_aeo','analyze_geo','analyze_seo','analyze_security','security_scan_enabled','vapt_enabled')
def configuration(value=None):
    result=dict(value or {})
    result.update(product_flow=FLOW,analysis_enabled=False,client_specific_pdf_enabled=False,static_company_pdf_enabled=False)
    result.update({key:False for key in AUDIT_FLAGS})
    result['lighthouse_budget']=0;result['deep_audit_budget']=0;result['opportunities']=[]
    if result.get('icp_id'):result['icp_id']=str(result['icp_id'])
    return result

def unavailable():
    from fastapi import HTTPException
    raise HTTPException(409,'Website assessments are not part of Lead Engine. Historical results are preserved; no new assessment was started.')
