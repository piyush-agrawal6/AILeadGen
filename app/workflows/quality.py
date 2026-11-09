"""Evidence-labelled contacts and one review workspace over existing operations."""
import json,uuid
from app.database.prospects import now

EMAIL_STATES=('PUBLICLY_PUBLISHED','PROVIDER_VERIFIED','DOMAIN_VALIDATED','UNVERIFIED','INVALID','HARD_BOUNCED','SUPPRESSED')

def contacts(c,pid,organization=None):
    from app.platform.context import organization as active_organization
    from fastapi import HTTPException
    organization=active_organization(organization)
    org_sql=(' AND p.organization_id=?' if organization else '');org_args=(organization,) if organization else ()
    lead=c.execute('SELECT p.lead_status,s.suppressed_at,m.contact_state FROM prospects p LEFT JOIN prospect_sales s ON s.prospect_id=p.id LEFT JOIN master_lead_state m ON m.prospect_id=p.id WHERE p.id=?'+org_sql,(pid,)+org_args).fetchone()
    if not lead:raise HTTPException(404,'Prospect not found in this workspace.')
    result=[]
    hard={r[0].lower() for r in c.execute("SELECT DISTINCT m.to_address FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.prospect_id=? AND e.event_type='BOUNCED_HARD' AND m.test_mode=0"+(' AND m.organization_id=?' if organization else ''),(pid,)+org_args).fetchall()}
    blocked={r['address'].lower():r['status'] for r in c.execute('SELECT address,status FROM email_address_suppressions'+(' WHERE organization_id=?' if organization else ''),(organization,) if organization else ()).fetchall()}
    for r in c.execute('SELECT x.*,e.verification_state,e.checked_at,e.checked_by,e.source_url evidence_source FROM contacts x JOIN businesses b ON b.id=x.business_id LEFT JOIN contact_evidence e ON e.contact_id=x.id WHERE b.prospect_id=? ORDER BY x.id DESC',(pid,)).fetchall():
        item=dict(r);email=item['contact_value'].lower();state=item['verification_state'] or ('PUBLICLY_PUBLISHED' if item['source_url'] and item['is_public_business_contact'] else 'UNVERIFIED')
        if item['contact_type']=='email':
            if email in hard:state='HARD_BOUNCED'
            elif lead and (lead['lead_status']=='DO_NOT_CONTACT' or lead['suppressed_at'] or lead['contact_state'] in ('DO_NOT_CONTACT','UNSUBSCRIBED')):state='SUPPRESSED'
            elif blocked.get(email)=='INVALID':state='INVALID'
            elif email in blocked:state='SUPPRESSED'
        item.update(email_state=state,domain_validated=bool(item['is_valid']),delivery_verified=state=='PROVIDER_VERIFIED')
        result.append(item)
    # A discovery/provider email without a published URL remains unverified.
    known={r['contact_value'].lower() for r in result if r['contact_type']=='email'}
    for b in c.execute('SELECT id,public_email,phone FROM businesses WHERE prospect_id=? ORDER BY id DESC',(pid,)).fetchall():
        if b['public_email'] and b['public_email'].lower() not in known:
            email=b['public_email'].lower();known.add(email)
            state='HARD_BOUNCED' if email in hard else 'SUPPRESSED' if lead and (lead['suppressed_at'] or lead['lead_status']=='DO_NOT_CONTACT' or lead['contact_state'] in ('DO_NOT_CONTACT','UNSUBSCRIBED')) else 'INVALID' if blocked.get(email)=='INVALID' else 'UNVERIFIED'
            result.append({'contact_type':'email','contact_value':email,'source_url':None,'email_state':state,'domain_validated':False,'delivery_verified':False,'source_type':'DISCOVERY_OBSERVATION'})
    people=[dict(r) for r in c.execute('SELECT * FROM contact_people WHERE prospect_id=?'+(' AND organization_id=?' if organization else '')+' ORDER BY created_at DESC',(pid,)+org_args).fetchall()]
    return {'contacts':result,'decision_makers':people,'missing_decision_maker_confidence':'UNKNOWN'}

REVIEW_SQL='''
 SELECT 'identity-'||CAST(b.id AS TEXT) id,b.prospect_id,b.id business_id,r.campaign_id,
 'Identity conflict' reason,b.name company,b.created_at created_at,'Review matching identity evidence' recommended_action
 FROM businesses b LEFT JOIN pipeline_runs r ON r.id=b.run_id WHERE b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED'
 UNION ALL SELECT 'outreach-'||i.id,i.prospect_id,i.business_id,w.campaign_id,
 'Report quality or pitch review',b.name,i.created_at,'Review stored findings, PDF and pitch'
 FROM outreach_run_items i JOIN businesses b ON b.id=i.business_id JOIN workflow_runs w ON w.id=i.run_id WHERE i.status='NEEDS_REVIEW'
 UNION ALL SELECT 'smtp-'||m.id,m.prospect_id,b.id,r.campaign_id,
 'Uncertain SMTP result',b.name,m.created_at,'Inspect Gmail Sent; do not retry automatically'
 FROM email_messages m JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id)
 LEFT JOIN pipeline_runs r ON r.id=b.run_id WHERE m.status='UNCERTAIN'
 UNION ALL SELECT 'contact-'||p.id,p.id,b.id,r.campaign_id,
 'Uncertain email',b.name,b.created_at,'Validate the public source and mail domain; do not infer delivery verification'
 FROM prospects p JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=p.id)
 LEFT JOIN pipeline_runs r ON r.id=b.run_id
 WHERE b.processing_status='QUALIFIED' AND b.public_email IS NOT NULL AND b.public_email<>''
 AND NOT EXISTS(SELECT 1 FROM contacts x JOIN businesses bx ON bx.id=x.business_id WHERE bx.prospect_id=p.id AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>'')
 UNION ALL SELECT x.id,x.prospect_id,x.business_id,x.campaign_id,x.reason,b.name,x.created_at,'Review evidence and record a decision'
 FROM review_cases x LEFT JOIN businesses b ON b.id=x.business_id WHERE x.status='OPEN' AND SUBSTR(x.id,1,9)<>'identity-' AND SUBSTR(x.id,1,9)<>'outreach-' AND SUBSTR(x.id,1,5)<>'smtp-' AND SUBSTR(x.id,1,8)<>'contact-'
'''

def reviews(c,search='',reason='',page=1,size=25,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    sql=REVIEW_SQL;org_args=[]
    if organization:
        org_args=[organization]*5
        sql=sql.replace("WHERE b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED'","WHERE b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED' AND r.organization_id=?")
        sql=sql.replace("WHERE i.status='NEEDS_REVIEW'","WHERE i.status='NEEDS_REVIEW' AND w.organization_id=?")
        sql=sql.replace("WHERE m.status='UNCERTAIN'","WHERE m.status='UNCERTAIN' AND m.organization_id=?")
        sql=sql.replace("AND NOT EXISTS(SELECT 1 FROM contacts x JOIN businesses bx ON bx.id=x.business_id WHERE bx.prospect_id=p.id AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>'')","AND p.organization_id=? AND NOT EXISTS(SELECT 1 FROM contacts x JOIN businesses bx ON bx.id=x.business_id WHERE bx.prospect_id=p.id AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>'')")
        sql=sql.replace("FROM review_cases x LEFT JOIN businesses b ON b.id=x.business_id WHERE x.status='OPEN'","FROM review_cases x LEFT JOIN businesses b ON b.id=x.business_id WHERE x.status='OPEN' AND x.organization_id=?")
    base=' FROM ('+sql+") x WHERE NOT EXISTS(SELECT 1 FROM review_cases resolved WHERE resolved.id=x.id AND resolved.status<>'OPEN')";args=list(org_args)
    if search:base+=' AND LOWER(COALESCE(x.company,\'\')) LIKE ?';args.append('%'+search.lower()+'%')
    if reason:base+=' AND x.reason=?';args.append(reason)
    total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
    items=[dict(r) for r in c.execute('SELECT *'+base+' ORDER BY created_at DESC LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()]
    return {'items':items,'total':total,'page':page,'page_size':size}

def quality(c,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    return dict(c.execute(('''SELECT
    (SELECT COUNT(*) FROM prospects WHERE organization_id=?) master_leads,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE public_email IS NOT NULL AND public_email<>'' AND prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)) with_email,
    (SELECT COUNT(DISTINCT b.prospect_id) FROM contacts x JOIN businesses b ON b.id=x.business_id JOIN prospects p ON p.id=b.prospect_id
     WHERE x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>''
     AND p.lead_status<>'DO_NOT_CONTACT' AND p.organization_id=? AND NOT EXISTS(SELECT 1 FROM email_address_suppressions s WHERE LOWER(s.address)=LOWER(x.contact_value) AND s.organization_id=p.organization_id AND s.status IN ('INVALID','TEMPORARILY_UNUSABLE'))
     AND NOT EXISTS(SELECT 1 FROM prospect_sales ps WHERE ps.prospect_id=p.id AND ps.suppressed_at IS NOT NULL)) with_usable_email,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE COALESCE(phone,normalized_phone) IS NOT NULL AND prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)) with_phone,
    (SELECT COUNT(DISTINCT prospect_id) FROM social_profiles WHERE prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)) with_social,
    (SELECT COUNT(DISTINCT prospect_id) FROM contact_people WHERE organization_id=?) with_decision_maker,
    (SELECT COUNT(*) FROM businesses WHERE rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED' AND prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)) possible_duplicates,
    (SELECT COUNT(*) FROM email_address_suppressions WHERE status='INVALID' AND organization_id=?) invalid_addresses,
    (SELECT COUNT(*) FROM prospect_sales WHERE suppressed_at IS NOT NULL AND organization_id=?) suppressed,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE (website IS NULL OR website='') AND prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)) missing_website
    ''' if organization else '''SELECT
    (SELECT COUNT(*) FROM prospects) master_leads,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE public_email IS NOT NULL AND public_email<>'') with_email,
    (SELECT COUNT(DISTINCT b.prospect_id) FROM contacts x JOIN businesses b ON b.id=x.business_id JOIN prospects p ON p.id=b.prospect_id
     WHERE x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>''
     AND p.lead_status<>'DO_NOT_CONTACT' AND NOT EXISTS(SELECT 1 FROM email_address_suppressions s WHERE LOWER(s.address)=LOWER(x.contact_value) AND s.organization_id=p.organization_id AND s.status IN ('INVALID','TEMPORARILY_UNUSABLE'))
     AND NOT EXISTS(SELECT 1 FROM prospect_sales ps WHERE ps.prospect_id=p.id AND ps.suppressed_at IS NOT NULL)) with_usable_email,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE COALESCE(phone,normalized_phone) IS NOT NULL) with_phone,
    (SELECT COUNT(DISTINCT prospect_id) FROM social_profiles) with_social,
    (SELECT COUNT(DISTINCT prospect_id) FROM contact_people) with_decision_maker,
    (SELECT COUNT(*) FROM businesses WHERE rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED') possible_duplicates,
    (SELECT COUNT(*) FROM email_address_suppressions WHERE status='INVALID') invalid_addresses,
    (SELECT COUNT(*) FROM prospect_sales WHERE suppressed_at IS NOT NULL) suppressed,
    (SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE website IS NULL OR website='') missing_website
    '''),(organization,)*10 if organization else ()).fetchone())
