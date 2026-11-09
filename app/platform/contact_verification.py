"""Owned deterministic contact checks; MX results never imply deliverability."""
import json
import uuid
from fastapi import HTTPException
from app.database.prospects import now
from app.platform.context import current,organization


def validate_domain(c,contact_id):
    org=organization();actor=current().actor
    contact=c.execute('''SELECT x.* FROM contacts x JOIN businesses b ON b.id=x.business_id
        JOIN pipeline_runs r ON r.id=b.run_id WHERE x.id=? AND x.contact_type='email'
        AND r.organization_id=? AND (b.prospect_id IS NULL OR EXISTS(
        SELECT 1 FROM prospects p WHERE p.id=b.prospect_id AND p.organization_id=?))''',(contact_id,org,org)).fetchone()
    if not contact:raise HTTPException(404,'Email contact not found in this workspace.')
    from app.enrichment.dns import check_email_dns
    _,valid=check_email_dns(contact['contact_value'])
    state='PUBLICLY_PUBLISHED' if valid and contact['source_url'] and contact['is_public_business_contact'] else 'DOMAIN_VALIDATED' if valid else 'UNVERIFIED'
    c.execute('UPDATE contacts SET is_valid=? WHERE id=?',(int(valid),contact_id))
    stamp=now()
    c.execute('INSERT INTO contact_evidence(contact_id,verification_state,source_url,checked_at,checked_by) VALUES(?,?,?,?,?) ON CONFLICT(contact_id) DO UPDATE SET verification_state=excluded.verification_state,checked_at=excluded.checked_at,checked_by=excluded.checked_by',(contact_id,state,contact['source_url'] or '',stamp,actor))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),actor,'CONTACT_DOMAIN_CHECKED','contact:'+str(contact_id),'SUCCESS',json.dumps({'domain_validated':bool(valid),'recipient_delivery_verified':False}),org,stamp))
    return {'email_state':state,'domain_validated':bool(valid),'recipient_delivery_verified':False}
