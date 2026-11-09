"""Explicit, transactional identity decisions; never merge on fuzzy evidence."""
import hashlib,re,uuid
from fastapi import HTTPException
from app.database.prospects import now
from app.workflows.history import encoded

def fingerprint(b):
    fields=('external_overture_id','external_osm_id','normalized_name','website','normalized_phone','public_email','address','city','country_code','country')
    return hashlib.sha256(encoded({k:getattr(b,k,None) for k in fields}).encode()).hexdigest()

def resolution_key(b,organization):
    return hashlib.sha256((organization+':'+fingerprint(b)).encode()).hexdigest()

def record_conflict(c,b,matched,cid=None,organization=None):
    from app.platform.context import organization as active_organization
    from app.platform.workspace import business_workspace
    organization=active_organization(organization)
    business_workspace(c,b,organization=organization,campaign_id=cid)
    marks=','.join('?' for _ in matched)
    count=c.execute('SELECT COUNT(*) FROM prospects WHERE organization_id=? AND id IN ('+marks+')',[organization,*matched]).fetchone()[0] if matched else 0
    if count!=len(matched):raise HTTPException(404,'Identity candidates do not belong to this workspace.')
    evidence={'candidate_prospect_ids':sorted(matched),'domain':b.domain,'phone':b.normalized_phone or b.phone,'company':b.name,'address':b.address,'email':b.public_email,'source_ids':{'overture':b.external_overture_id,'osm':b.external_osm_id}}
    c.execute("INSERT INTO review_cases(id,business_id,campaign_id,reason,evidence_json,created_at,organization_id) VALUES(?,?,?,'Identity conflict',?,?,?) ON CONFLICT(id) DO UPDATE SET evidence_json=excluded.evidence_json",('identity-'+str(b.id),b.id,cid,encoded(evidence),now(),organization))

def keep_separate(c,b,actor,organization=None):
    from app.platform.context import organization as active_organization
    from app.platform.workspace import business_workspace
    organization=active_organization(organization)
    business_workspace(c,b,organization=organization)
    pid=str(uuid.uuid4());stamp=now()
    cid=c.execute('SELECT r.campaign_id FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.id=?',(b.id,)).fetchone()
    c.execute('INSERT INTO prospects(id,first_seen_at,last_seen_at,updated_at,created_by,first_campaign_id,organization_id) VALUES(?,?,?,?,?,?,?)',(pid,stamp,stamp,stamp,actor,cid[0] if cid else None,organization))
    c.execute("INSERT INTO identity_resolutions(fingerprint,prospect_id,decision,actor,created_at) VALUES(?,?,'KEEP_SEPARATE',?,?) ON CONFLICT(fingerprint) DO UPDATE SET prospect_id=excluded.prospect_id,actor=excluded.actor,created_at=excluded.created_at",(resolution_key(b,organization),pid,actor,stamp))
    from app.database.prospects import ProspectRepository
    ProspectRepository(c).observe(b,created_by=actor,organization=organization)
    c.execute("UPDATE businesses SET is_rejected=0,rejection_reason=NULL,processing_status='DISCOVERED' WHERE id=?",(b.id,))
    return pid

def references(c):
    if getattr(c,'backend',None)=='postgres':
        return [(r[0],r[1]) for r in c.execute('''SELECT k.table_name,k.column_name FROM information_schema.table_constraints t
          JOIN information_schema.key_column_usage k ON k.constraint_name=t.constraint_name AND k.constraint_schema=t.constraint_schema
          JOIN information_schema.constraint_column_usage u ON u.constraint_name=t.constraint_name AND u.constraint_schema=t.constraint_schema
          WHERE t.constraint_type='FOREIGN KEY' AND u.table_name='prospects' AND k.table_schema=?''',(getattr(c,'schema','public'),)).fetchall()]
    refs=[]
    for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        if re.fullmatch('[a-z_]+',row[0]):
            refs.extend((row[0],fk['from']) for fk in c.execute('PRAGMA foreign_key_list('+row[0]+')').fetchall() if fk['table']=='prospects')
    return refs

def merge(c,source,target,actor):
    from app.platform.context import organization
    from app.api.permissions import require_owner
    org=organization();require_owner(c,actor,org)
    if source==target:raise HTTPException(422,'Choose two different Master Leads.')
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT pg_advisory_xact_lock(691944307)');c.execute('SELECT id FROM prospects WHERE organization_id=? AND id IN (?,?) ORDER BY id FOR UPDATE',(org,source,target))
    records={r['id']:dict(r) for r in c.execute('SELECT * FROM prospects WHERE organization_id=? AND id IN (?,?)',(org,source,target)).fetchall()}
    if len(records)!=2:raise HTTPException(404,'Both Master Leads must exist.')
    if c.execute("SELECT 1 FROM email_messages WHERE prospect_id IN (?,?) AND status IN ('SENDING','UNCERTAIN') LIMIT 1",(source,target)).fetchone():raise HTTPException(409,'Resolve active or uncertain SMTP sends before merging.')
    if c.execute("SELECT 1 FROM outreach_run_items i JOIN workflow_runs r ON r.id=i.run_id WHERE i.prospect_id IN (?,?) AND r.status IN ('RUNNING','PREPARING') LIMIT 1",(source,target)).fetchone():raise HTTPException(409,'Pause related outreach before merging.')
    refs=references(c);archive={'source':records[source],'related':{}}
    for table,column in refs:
        if not re.fullmatch('[a-z_]+',table+column):raise RuntimeError('Unexpected reference identifier')
        archive['related'][table]=[dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE '+column+'=?',(source,)).fetchall()]
    c.execute('SAVEPOINT duplicate_merge')
    try:
        for table in ('master_lead_state','prospect_sales','automation_email_queue'):
            a=c.execute('SELECT * FROM '+table+' WHERE prospect_id=?',(source,)).fetchone();b=c.execute('SELECT * FROM '+table+' WHERE prospect_id=?',(target,)).fetchone()
            if a and b:
                if table=='master_lead_state':
                    priority=['DO_NOT_CONTACT','UNSUBSCRIBED','EMAIL_BOUNCED','REPLIED','CONNECTED_MANUALLY','EMAIL_SENT','EMAIL_QUEUED','READY_TO_EMAIL','NOT_CONTACTED']
                    chosen=min((a,b),key=lambda r:priority.index(r['contact_state']) if r['contact_state'] in priority else len(priority))
                    c.execute('UPDATE master_lead_state SET contact_state=?,updated_at=? WHERE prospect_id=?',(chosen['contact_state'],now(),target))
                elif table=='prospect_sales':
                    c.execute('UPDATE prospect_sales SET suppressed_at=COALESCE(suppressed_at,?),last_contact_at=?,unread_replies=? WHERE prospect_id=?',(a['suppressed_at'],max(a['last_contact_at'] or '',b['last_contact_at'] or '') or None,(a['unread_replies'] or 0)+(b['unread_replies'] or 0),target))
                else:c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=?",(target,))
                c.execute('DELETE FROM '+table+' WHERE prospect_id=?',(source,))
        c.execute('DELETE FROM analysis_cache WHERE prospect_id IN (?,?)',(source,target))
        c.execute('DELETE FROM prospect_observations WHERE prospect_id=? AND run_id IN (SELECT run_id FROM prospect_observations WHERE prospect_id=?)',(source,target))
        for table,column in refs:
            if table!='analysis_cache':c.execute('UPDATE '+table+' SET '+column+'=? WHERE '+column+'=?',(target,source))
        strict=['DO_NOT_CONTACT','NOT_INTERESTED','WON','LOST','REPLIED','MEETING','PROPOSAL','CONTACTED']
        selected=min([records[source]['lead_status'],records[target]['lead_status']],key=lambda v:strict.index(v) if v in strict else len(strict))
        c.execute('UPDATE prospects SET lead_status=?,first_seen_at=?,last_seen_at=?,updated_at=? WHERE id=?',(selected,min(records[source]['first_seen_at'],records[target]['first_seen_at']),max(records[source]['last_seen_at'],records[target]['last_seen_at']),now(),target))
        c.execute('UPDATE prospects SET times_discovered=(SELECT COUNT(*) FROM prospect_observations WHERE prospect_id=?) WHERE id=?',(target,target))
        c.execute('INSERT INTO duplicate_resolutions(source_id,target_id,archived_json,created_at,actor) VALUES(?,?,?,?,?)',(source,target,encoded(archive),now(),actor))
        c.execute('DELETE FROM prospects WHERE id=?',(source,))
        c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=?",(target,))
        c.execute('RELEASE SAVEPOINT duplicate_merge')
        return {'merged':True,'canonical_prospect_id':target,'history_archived':True,'automatic_sending_resumed':False}
    except Exception:
        c.execute('ROLLBACK TO SAVEPOINT duplicate_merge');c.execute('RELEASE SAVEPOINT duplicate_merge')
        raise HTTPException(409,'Overlapping history requires individual review. No merge was applied and all original records remain intact.') from None
