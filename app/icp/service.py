"""Versioned ICP storage. Saving criteria never starts discovery or outreach."""
import hashlib
import json
import uuid
from fastapi import HTTPException
from app.api.organization import require_role,membership_role
from app.database.prospects import now
from app.platform.context import organization,current
from app.icp.models import Create,Update,Profile


def _lock(c,org):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')


def _editable(c,org):
    require_role(c,current().actor,org,('OWNER','ADMIN'))


def _owned(c,key):
    org=organization()
    row=c.execute("SELECT * FROM ideal_customer_profiles WHERE id=? AND organization_id=?",(key,org)).fetchone()
    if not row:raise HTTPException(404,'Ideal customer profile not found.')
    return dict(row)


def _profile(row):
    return Profile.model_validate({key:value for key,value in row.items() if key in Profile.model_fields and key!='criteria'}|{'criteria':json.loads(row['criteria_json'])}).model_dump(mode='json')


def get(c,key):
    row=_owned(c,key)
    if row['status']=='DELETED':raise HTTPException(404,'Ideal customer profile not found.')
    return _profile(row)


def listing(c,page=1,status=None):
    org=organization();where="organization_id=? AND status<>'DELETED'";args=[org]
    if status:where+=' AND status=?';args.append(status)
    total=c.execute('SELECT COUNT(*) FROM ideal_customer_profiles WHERE '+where,args).fetchone()[0]
    rows=c.execute('SELECT * FROM ideal_customer_profiles WHERE '+where+' ORDER BY updated_at DESC,id LIMIT 25 OFFSET ?',args+[(page-1)*25]).fetchall()
    return {'items':[_profile(dict(row)) for row in rows],'total':total,'page':page,'page_size':25,'can_edit':membership_role(c,current().actor,org) in ('OWNER','ADMIN')}


def _record(c,key,action):
    org=organization();actor=current().actor;profile=get(c,key);stamp=now()
    c.execute('INSERT INTO icp_versions(icp_id,organization_id,revision,snapshot_json,changed_by,created_at) VALUES(?,?,?,?,?,?)',
        (key,org,profile['revision'],json.dumps(profile,sort_keys=True),actor,stamp))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,action,'icp:'+key,'SUCCESS',json.dumps({'revision':profile['revision']}),org,stamp))
    return profile


def create(c,body:Create):
    org=organization();actor=current().actor;_editable(c,org);_lock(c,org);_editable(c,org)
    encoded=json.dumps(body.model_dump(mode='json',exclude={'request_id'}),sort_keys=True)
    digest=hashlib.sha256(encoded.encode()).hexdigest()
    prior=c.execute('SELECT id,creation_fingerprint FROM ideal_customer_profiles WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
    if prior:
        if prior['creation_fingerprint']!=digest:raise HTTPException(409,'This creation request already belongs to different targeting criteria.')
        return get(c,prior['id'])
    from app.config.settings import get_settings
    count=c.execute("SELECT COUNT(*) FROM ideal_customer_profiles WHERE organization_id=? AND status<>'DELETED'",(org,)).fetchone()[0]
    if count>=get_settings().heysow_icp_limit:raise HTTPException(409,'This workspace has reached its configured ICP safety limit.')
    source,metadata='MANUAL','{}'
    if body.ai_proposal_id:
        from app.icp.builder import provenance
        source,metadata=provenance(c,body.ai_proposal_id)
    key=str(uuid.uuid4());stamp=now()
    c.execute('''INSERT INTO ideal_customer_profiles(id,organization_id,name,description,status,criteria_json,revision,request_id,creation_fingerprint,created_by,updated_by,created_at,updated_at)
        VALUES(?,?,?,?,?,?,1,?,?,?,?,?,?)''',(key,org,body.name,body.description,body.status,body.criteria.model_dump_json(),str(body.request_id),digest,actor,actor,stamp,stamp))
    c.execute('UPDATE ideal_customer_profiles SET generation_source=?,generation_metadata_json=? WHERE id=? AND organization_id=?',(source,metadata,key,org))
    return _record(c,key,'ICP_CREATED')


def update(c,key,body:Update):
    org=organization();_editable(c,org);_lock(c,org);_editable(c,org)
    previous=get(c,key)
    if body.revision!=previous['revision']:raise HTTPException(409,'This ICP changed. Reload the latest version before saving.')
    fields=body.model_dump(mode='json',exclude={'revision','ai_proposal_id'})
    if all(previous[name]==value for name,value in fields.items()):return previous
    if body.ai_proposal_id:
        from app.icp.builder import provenance
        source,metadata=provenance(c,body.ai_proposal_id)
        c.execute('UPDATE ideal_customer_profiles SET generation_source=?,generation_metadata_json=? WHERE id=? AND organization_id=?',(source,metadata,key,org))
    c.execute('UPDATE ideal_customer_profiles SET name=?,description=?,status=?,criteria_json=?,revision=revision+1,updated_by=?,updated_at=? WHERE id=? AND organization_id=? AND revision=?',
        (body.name,body.description,body.status,body.criteria.model_dump_json(),current().actor,now(),key,org,body.revision))
    return _record(c,key,'ICP_UPDATED')


def history(c,key,page=1):
    _owned(c,key);org=organization()
    total=c.execute('SELECT COUNT(*) FROM icp_versions WHERE icp_id=? AND organization_id=?',(key,org)).fetchone()[0]
    rows=c.execute('SELECT revision,snapshot_json,changed_by,created_at FROM icp_versions WHERE icp_id=? AND organization_id=? ORDER BY revision DESC LIMIT 25 OFFSET ?',(key,org,(page-1)*25)).fetchall()
    return {'items':[{'revision':r['revision'],'snapshot':json.loads(r['snapshot_json']),'changed_by':r['changed_by'],'created_at':r['created_at']} for r in rows],'total':total,'page':page,'page_size':25}


def duplicate(c,key,body):
    source=get(c,key)
    return create(c,Create(name=body.name,description=source['description'],criteria=source['criteria'],status='INACTIVE',request_id=body.request_id))


def compare(c,key,before,after):
    _owned(c,key);org=organization();snapshots={}
    for revision in (before,after):
        row=c.execute('SELECT snapshot_json FROM icp_versions WHERE icp_id=? AND organization_id=? AND revision=?',(key,org,revision)).fetchone()
        if not row:raise HTTPException(404,'ICP version not found.')
        snapshots[revision]=json.loads(row[0])
    left,right=snapshots[before],snapshots[after]
    changed={name:{'before':left[name],'after':right[name]} for name in ('name','description','status','criteria') if left[name]!=right[name]}
    return {'before_revision':before,'after_revision':after,'changes':changed}
