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


def _primary_icp_id(c, org) -> str | None:
    try:
        row = c.execute(
            'SELECT configuration_json FROM intent_preferences WHERE organization_id=?',
            (org,),
        ).fetchone()
        if row and row['configuration_json']:
            return json.loads(row['configuration_json']).get('default_icp_id')
    except Exception:
        return None
    return None


def _related_counts(c, org, icp_id: str) -> dict[str, int]:
    counts = {'discoveries': 0, 'monitors': 0}
    try:
        d_rows = c.execute(
            'SELECT configuration_json FROM intent_discoveries WHERE organization_id=? ORDER BY created_at DESC LIMIT 200',
            (org,),
        ).fetchall()
        counts['discoveries'] = sum(1 for r in d_rows if icp_id in (r['configuration_json'] or ''))
    except Exception:
        pass
    try:
        m_rows = c.execute(
            'SELECT configuration_json FROM intent_monitors WHERE organization_id=? LIMIT 100',
            (org,),
        ).fetchall()
        counts['monitors'] = sum(1 for r in m_rows if icp_id in (r['configuration_json'] or ''))
    except Exception:
        pass
    return counts


def _profile(row, *, primary_id: str | None = None, counts: dict[str, int] | None = None):
    payload = (
        {key: value for key, value in row.items() if key in Profile.model_fields and key not in ('criteria', 'is_primary', 'related_counts')}
        | {
            'criteria': json.loads(row['criteria_json']),
            'is_primary': bool(primary_id and str(row['id']) == str(primary_id)),
            'related_counts': counts or {},
        }
    )
    return Profile.model_validate(payload).model_dump(mode='json')


def get(c,key):
    row=_owned(c,key)
    if row['status']=='DELETED':raise HTTPException(404,'Ideal customer profile not found.')
    org=organization()
    return _profile(row, primary_id=_primary_icp_id(c, org), counts=_related_counts(c, org, str(row['id'])))


def listing(c,page=1,status=None):
    org=organization();where="organization_id=? AND status<>'DELETED'";args=[org]
    if status:where+=' AND status=?';args.append(status)
    total=c.execute('SELECT COUNT(*) FROM ideal_customer_profiles WHERE '+where,args).fetchone()[0]
    rows=c.execute('SELECT * FROM ideal_customer_profiles WHERE '+where+' ORDER BY updated_at DESC,id LIMIT 25 OFFSET ?',args+[(page-1)*25]).fetchall()
    primary_id=_primary_icp_id(c, org)
    items=[_profile(dict(row), primary_id=primary_id, counts=_related_counts(c, org, str(row['id']))) for row in rows]
    items.sort(key=lambda x: (0 if x.get('is_primary') else 1, 0 if x.get('status') == 'ACTIVE' else 1))
    return {'items':items,'total':total,'page':page,'page_size':25,'can_edit':membership_role(c,current().actor,org) in ('OWNER','ADMIN')}


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


def set_primary(c, key: str):
    org = organization()
    _editable(c, org)
    _lock(c, org)
    profile = get(c, key)
    row = c.execute('SELECT configuration_json, revision FROM intent_preferences WHERE organization_id=?', (org,)).fetchone()
    stamp = now()
    if row:
        cfg = json.loads(row['configuration_json'])
        cfg['default_icp_id'] = key
        c.execute(
            'UPDATE intent_preferences SET configuration_json=?, revision=revision+1, updated_at=? WHERE organization_id=?',
            (json.dumps(cfg), stamp, org),
        )
    else:
        cfg = {'default_icp_id': key, 'default_view': 'table', 'min_relevance': 35, 'topics': [], 'alerts_enabled': True, 'alert_threshold': 70, 'source_retention_days': 30}
        c.execute(
            'INSERT INTO intent_preferences(organization_id, configuration_json, revision, updated_at) VALUES(?,?,1,?)',
            (org, json.dumps(cfg), stamp),
        )
    c.execute(
        'INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()), current().actor, 'ICP_PRIMARY_SET', 'icp:' + key, 'SUCCESS', json.dumps({'name': profile['name']}), org, stamp),
    )
    return get(c, key)


def delete(c, key: str):
    org = organization()
    _editable(c, org)
    _lock(c, org)
    profile = get(c, key)
    stamp = now()
    c.execute(
        "UPDATE ideal_customer_profiles SET status='DELETED', revision=revision+1, updated_by=?, updated_at=? WHERE id=? AND organization_id=?",
        (current().actor, stamp, key, org),
    )
    if _primary_icp_id(c, org) == key:
        row = c.execute('SELECT configuration_json FROM intent_preferences WHERE organization_id=?', (org,)).fetchone()
        if row:
            cfg = json.loads(row['configuration_json'])
            cfg['default_icp_id'] = None
            c.execute(
                'UPDATE intent_preferences SET configuration_json=?, revision=revision+1, updated_at=? WHERE organization_id=?',
                (json.dumps(cfg), stamp, org),
            )
    c.execute(
        'INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()), current().actor, 'ICP_DELETED', 'icp:' + key, 'SUCCESS', json.dumps({'name': profile['name']}), org, stamp),
    )
    return {'deleted': True, 'id': key}


def _icp_terms(profile: dict) -> list[str]:
    crit = profile.get('criteria') or {}
    comp = crit.get('company') or {}
    cont = crit.get('contact') or {}
    intent = crit.get('intent') or {}
    raw = [
        *(comp.get('industries') or []),
        *(comp.get('technologies') or []),
        *(cont.get('job_titles') or []),
        *(intent.get('business_needs') or []),
        *(intent.get('pain_points') or []),
        *(intent.get('buying_signals') or []),
        *(intent.get('search_terms') or []),
        *(intent.get('competitors') or []),
    ]
    terms = []
    for item in raw:
        t = str(item).strip().casefold()
        if len(t) >= 3 and t not in terms:
            terms.append(t)
    return terms[:40]


def related(c, key: str):
    org = organization()
    profile = get(c, key)
    discoveries = []
    monitors = []
    signals = []
    try:
        for r in c.execute(
            'SELECT id, title, status, created_at, configuration_json FROM intent_discoveries WHERE organization_id=? ORDER BY created_at DESC LIMIT 100',
            (org,),
        ).fetchall():
            if key in (r['configuration_json'] or ''):
                discoveries.append({'id': r['id'], 'title': r['title'], 'status': r['status'], 'created_at': r['created_at']})
    except Exception:
        pass
    try:
        for r in c.execute(
            'SELECT id, name, status, last_checked, configuration_json FROM intent_monitors WHERE organization_id=? ORDER BY created_at DESC LIMIT 100',
            (org,),
        ).fetchall():
            if key in (r['configuration_json'] or ''):
                monitors.append({'id': r['id'], 'name': r['name'], 'status': r['status'], 'last_checked': r['last_checked']})
    except Exception:
        pass
    terms = _icp_terms(profile)
    if terms:
        try:
            for r in c.execute(
                'SELECT id, title, source, score, category, observed_at, excerpt FROM intent_signals WHERE organization_id=? AND available=1 ORDER BY observed_at DESC LIMIT 200',
                (org,),
            ).fetchall():
                hay = f"{r['title']} {r['excerpt']}".casefold()
                matched = [t for t in terms if t in hay]
                if matched:
                    signals.append({
                        'id': r['id'],
                        'title': r['title'],
                        'source': r['source'],
                        'score': r['score'],
                        'category': r['category'],
                        'observed_at': r['observed_at'],
                        'matched_terms': matched[:4],
                    })
                    if len(signals) >= 15:
                        break
        except Exception:
            pass
    return {'icp_id': key, 'discoveries': discoveries[:15], 'monitors': monitors[:15], 'signals': signals}


def compare_profiles(c, profile_ids: list[str] | None = None):
    org = organization()
    all_profiles = listing(c, page=1)['items']
    selected = [p for p in all_profiles if not profile_ids or p['id'] in profile_ids][:6]
    sig_rows = []
    try:
        sig_rows = c.execute(
            'SELECT id, title, excerpt, score, source, observed_at FROM intent_signals WHERE organization_id=? AND available=1 ORDER BY observed_at DESC LIMIT 250',
            (org,),
        ).fetchall()
    except Exception:
        pass
    rows = []
    for p in selected:
        crit = p.get('criteria') or {}
        comp = crit.get('company') or {}
        cont = crit.get('contact') or {}
        intent = crit.get('intent') or {}
        missing = []
        if not comp.get('industries'): missing.append('Target industries')
        if not cont.get('job_titles'): missing.append('Decision-maker job titles')
        if not intent.get('pain_points'): missing.append('Business pain points')
        if not intent.get('buying_signals'): missing.append('Buying triggers')
        if not intent.get('exclusions'): missing.append('Exclusion criteria')
        if not intent.get('search_terms'): missing.append('Search terminology')
        terms = _icp_terms(p)
        matched_signals = 0
        high_intent_matches = 0
        for s in sig_rows:
            hay = f"{s['title']} {s['excerpt']}".casefold()
            if any(t in hay for t in terms):
                matched_signals += 1
                if int(s['score'] or 0) >= 65:
                    high_intent_matches += 1
        completeness = max(0, 100 - len(missing) * 15)
        rows.append({
            'id': p['id'],
            'name': p['name'],
            'status': p['status'],
            'is_primary': p.get('is_primary', False),
            'industries': comp.get('industries', [])[:5],
            'job_titles': cont.get('job_titles', [])[:5],
            'pain_points_count': len(intent.get('pain_points', [])),
            'buying_signals_count': len(intent.get('buying_signals', [])),
            'matched_signals': matched_signals,
            'high_intent_matches': high_intent_matches,
            'completeness_score': completeness,
            'missing_fields': missing,
        })
    recommended = max(rows, key=lambda r: (r['high_intent_matches'], r['matched_signals'], r['completeness_score'])) if rows else None
    return {
        'items': rows,
        'recommended_id': recommended['id'] if recommended else None,
        'recommendation_reason': (
            f"{recommended['name']} leads with {recommended['high_intent_matches']} high-relevance signal matches ({recommended['matched_signals']} total) and {recommended['completeness_score']}% targeting completeness."
            if recommended
            else 'Add at least one ICP to compare targeting coverage.'
        ),
        'signals_evaluated': len(sig_rows),
    }
