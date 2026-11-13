"""Dry-run by default: grant only the verified existing PlaneByte admin workspace."""
import argparse,asyncio,json,uuid
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.migrations import verify_schema
from app.database.prospects import now
from app.platform.context import workspace_scope

def candidate(c,owner):
    if get_settings().allowed_emails!=[owner]:raise RuntimeError('The runtime must restrict login to the one approved owner first.')
    rows=c.execute("SELECT o.id,o.name,m.role,b.status onboarding FROM organizations o JOIN organization_memberships m ON m.organization_id=o.id AND m.user_id=? AND m.status='ACTIVE' JOIN organization_onboarding b ON b.organization_id=o.id WHERE o.slug='planebyte' AND o.status='ACTIVE' AND m.role IN ('OWNER','ADMIN')",(owner,)).fetchall()
    if len(rows)!=1 or rows[0]['onboarding']!='COMPLETED':raise RuntimeError('Exactly one active, completed PlaneByte workspace with approved owner/admin membership is required.')
    return dict(rows[0])

def grant(c,owner,*,apply=False):
    verify_schema(c);row=candidate(c,owner)
    result={'organization_id':row['id'],'workspace':row['name'],'verified_role':row['role'],'owner':owner,'mode':'apply' if apply else 'dry-run','other_workspaces_changed':False}
    if not apply:return result
    with workspace_scope(c,owner,row['id']):
        if not c.execute("UPDATE organizations SET status=status WHERE id=? AND status='ACTIVE'",(row['id'],)).rowcount:raise RuntimeError('Workspace authority changed.')
        if not c.execute("UPDATE organization_memberships SET role=role WHERE organization_id=? AND user_id=? AND status='ACTIVE' AND role IN ('OWNER','ADMIN')",(row['id'],owner)).rowcount:raise RuntimeError('Owner authority changed.')
        if not c.execute("UPDATE organization_onboarding SET status=status WHERE organization_id=? AND status='COMPLETED'",(row['id'],)).rowcount:raise RuntimeError('Workspace setup changed.')
        candidate(c,owner)
        changed=c.execute("UPDATE organization_products SET enabled=1,updated_at=? WHERE organization_id=? AND product='INTENT_RADAR' AND enabled=0",(now(),row['id'])).rowcount
        if changed:c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),owner,'OWNER_APPROVED_RADAR_BETA','organization:'+row['id'],'SUCCESS',json.dumps({'approval':'Owner-approved existing PlaneByte admin workspace only; 2026-11-13'}),row['id'],now()))
        actual=c.execute("SELECT enabled FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR'",(row['id'],)).fetchone()
        if not actual or not actual[0]:raise RuntimeError('Existing product grant could not be verified.')
    result['enabled']=True;result['changed']=bool(changed);return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    with db_session() as c:result=grant(c,'planebyte@gmail.com',apply=args.apply)
    if args.apply:
        from app.api.read_cache import read_cache
        asyncio.run(read_cache.invalidate())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
