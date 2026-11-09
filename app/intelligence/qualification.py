"""Read-only owned qualification previews; applying a lifecycle remains explicit."""
import json
from app.people.service import company,get as person
from app.database.repositories import BusinessRepository
from app.icp.service import get as profile
from app.prospecting.intake import resolve_profile
from app.icp.matching import evaluate
from fastapi import HTTPException


def match(c,business_id,profile_id=None,contact_id=None):
    parent=company(c,business_id);business=BusinessRepository(c).get_by_id(business_id)
    contact=person(c,contact_id) if contact_id else None
    if contact and contact['prospect_id']!=parent['prospect_id']:raise HTTPException(409,'Choose a contact belonging to this company.')
    selected=profile(c,str(profile_id)) if profile_id else resolve_profile(c,{})
    facts=json.loads(parent['source_tags_json'] or '{}').get('company_intelligence',{})
    return evaluate(selected,business,facts,contact)


def recommendations(c,profile_id,page=1,size=25):
    from app.people.service import ctx
    org=ctx(c).organization_id;selected=profile(c,str(profile_id))
    # Evaluate only a bounded owned page. No fictitious global rank or provider call.
    rows=c.execute('''SELECT b.*,(SELECT COUNT(*) FROM contact_people p WHERE p.prospect_id=b.prospect_id AND p.organization_id=? AND p.archived_at IS NULL) professional_contact_count
        FROM businesses b WHERE b.id IN (SELECT MAX(x.id) FROM businesses x JOIN pipeline_runs r ON r.id=x.run_id
        WHERE r.organization_id=? AND x.prospect_id IS NOT NULL GROUP BY x.prospect_id)
        ORDER BY b.id DESC LIMIT ? OFFSET ?''',(org,org,size+1,(page-1)*size)).fetchall()
    items=[]
    for row in rows[:size]:
        b=BusinessRepository(c)._row_to_business(row);facts=json.loads(b.source_tags or '{}').get('company_intelligence',{});fit=evaluate(selected,b,facts)
        items.append({'business_id':b.id,'name':b.name,'qualification_status':b.processing_status,'professional_contact_count':row['professional_contact_count'],'fit':fit,'suggested_action':'REVIEW_MISSING_EVIDENCE' if fit['coverage'] is None or fit['coverage']<100 else 'REVIEW_COMPANY'})
    return {'items':sorted(items,key=lambda item:(item['fit']['score'] or 0,item['fit']['coverage'] or 0),reverse=True),'page':page,'page_size':size,'ranking_scope':'CURRENT_PAGE_ONLY','has_more':len(rows)>size,'discovery_started':False,'outreach_started':False}
