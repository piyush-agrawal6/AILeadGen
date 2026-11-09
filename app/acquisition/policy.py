"""Source-specific qualification; email delivery protections remain independent."""
from dataclasses import dataclass
from enum import StrEnum

class ProcessingPolicy(StrEnum):
    DISCOVERY_QUALIFIED='DISCOVERY_QUALIFIED'
    EMAIL_CONTACTABLE_DISCOVERY='EMAIL_CONTACTABLE_DISCOVERY'
    TRUSTED_IMPORT='TRUSTED_IMPORT'

@dataclass(frozen=True)
class SourcePolicy:
    mode:ProcessingPolicy
    trusted_import:bool=False
    email_before_analysis:bool=False
    opportunity_gate:bool=False
    business_fit_gate:bool=True
    @property
    def label(self):
        return {ProcessingPolicy.DISCOVERY_QUALIFIED:'Discovery Qualification',ProcessingPolicy.EMAIL_CONTACTABLE_DISCOVERY:'Email-Contactable Discovery',ProcessingPolicy.TRUSTED_IMPORT:'Trusted Import'}[self.mode]

DISCOVERY=SourcePolicy(ProcessingPolicy.DISCOVERY_QUALIFIED,email_before_analysis=False)
CONTACTABLE=SourcePolicy(ProcessingPolicy.EMAIL_CONTACTABLE_DISCOVERY,email_before_analysis=True,opportunity_gate=False,business_fit_gate=False)
IMPORTED=SourcePolicy(ProcessingPolicy.TRUSTED_IMPORT,trusted_import=True,opportunity_gate=False,business_fit_gate=False)

def policy(source='OVERTURE'):
    source=str(source or 'OVERTURE').upper()
    if source=='FIRECRAWL':return CONTACTABLE
    if source in ('FILE_IMPORT','CSV','XLSX','GOOGLE_SHEETS'):return IMPORTED
    return DISCOVERY

def configured_policy(configuration):
    """Resolve source behavior; historical assessment flags do not authorize audits."""
    if not configuration or not(configuration.get('source_type') or configuration.get('processing_policy')):return None
    return policy(configuration.get('source_type','OVERTURE'))

def valid_email(value):
    from app.mail.service import address
    from fastapi import HTTPException
    if not value:return None
    try:return address(str(value).strip())
    except HTTPException:return None

def published_email(b,fields=None):
    """Require observed public evidence, never a synthesized mailbox pattern."""
    from app.enrichment.contacts import is_valid_business_email
    from app.utils.urls import is_safe_url,extract_domain
    email=valid_email(getattr(b,'public_email',None) if not isinstance(b,dict) else b.get('email') or b.get('public_email'))
    if not email or not is_valid_business_email(email):return None
    if fields is not None:
        evidence=fields.get('email') or {};url=evidence.get('url')
        if evidence.get('verification') not in ('PUBLICLY_PUBLISHED','OBSERVED_PUBLIC_PAGE') or not isinstance(url,str) or not is_safe_url(url,check_dns=False):return None
    return email

def owner_imported_emails(c,cids=None):
    """Owner-provided addresses are trusted input, not claimed public evidence."""
    import json
    from app.database.acquisition_schema import ready
    if not ready(c):return set()
    version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
    org=None
    if version>=16:
        from app.platform.context import organization
        org=organization()
    condition=' AND e.campaign_id IN ('+','.join('?' for _ in cids)+')' if cids else ''
    if org:condition+=' AND b.prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)'
    args=list(cids or [])+([org] if org else [])
    rows=c.execute("SELECT b.prospect_id,b.public_email,e.field_sources_json FROM lead_source_evidence e JOIN businesses b ON b.id=e.business_id WHERE e.source_type IN ('FILE_IMPORT','GOOGLE_SHEETS') AND b.processing_status='QUALIFIED'"+condition,args).fetchall()
    result=set()
    for row in rows:
        fields=json.loads(row['field_sources_json']);evidence=fields.get('email') or {};email=valid_email(row['public_email'])
        if email and evidence.get('verification')=='OWNER_PROVIDED' and valid_email(evidence.get('value'))==email:result.add((row['prospect_id'],email))
    return result
