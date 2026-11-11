"""Explicit, bounded live HN acceptance in a NEW disposable SQLite database.

No account credentials, email, AI, company acquisition or production database is used.
Pass --database in data/e2e/ or the approved OpenCode temporary directory.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.intent_radar import models,service,discovery
from app.intelligence import jobs

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database',required=True)
args=parser.parse_args();root=Path(__file__).resolve().parents[1];path=Path(args.database).resolve()
temporary=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
if path.exists() or not path.parent.exists() or not (path.is_relative_to(root/'data/e2e') or path.is_relative_to(temporary)):
    parser.error('Use a new database path within an existing isolated test directory. Existing databases are never reset.')
settings=get_settings();settings.app_env='test';settings.database_path=str(path);settings.intent_radar_stage='Beta'
settings.intent_radar_ai_enabled=False
settings.allowed_user_emails='intent-acceptance@example.test'
c=get_connection(path);run_migrations(c)
actor='intent-acceptance@example.test'
org=create_organization(c,actor,'Intent Radar live acceptance')['organization_id']
other=create_organization(c,actor,'Second isolated acceptance workspace')['organization_id']
c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id IN (?,?)",(org,other))
c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id IN (?,?) AND product='INTENT_RADAR'",(org,other));c.commit()
with workspace_scope(c,actor,org):
    monitor=service.save_monitor(c,models.Monitor(name='Recent Ask HN technology conversations',goal='Review public technology discussions',configuration=models.Search(keywords=['ask hn'],result_limit=20),status='Active'))
    body=models.Discovery(configuration=models.Search.model_validate(monitor['configuration']),monitor_id=monitor['id'])
    job=discovery.create(c,body);c.commit();jobs.execute(job['id'],path)
    result=discovery.owned_job(c,job['id'])
    records=service.listing(c,'signals')['items']
    if result['status']!='COMPLETED' or not records:
        print(json.dumps({'live_discovery':'BLOCKED_OR_NO_MATCHES','job_status':result['status'],'errors':[i['error_code'] for i in result['items']],'database':str(path)}));raise SystemExit(1)
    signal=records[0];service.bookmark(c,signal['id']);opportunity=service.opportunity(c,signal['id'])
    service.opportunity(c,opportunity['id'],models.OpportunityUpdate(revision=opportunity['revision'],status='Reviewing',priority='High',notes='Source-backed acceptance run. Human review is still required.'))
    c.commit();counts=service.overview(c)
    assert not result['items'][0]['result']['synthetic'] and signal['source_url'].startswith('https://news.ycombinator.com/item?id=')
with workspace_scope(c,actor,other):
    assert service.listing(c,'signals')['total']==0 and service.saved(c)['items']==[]
    from fastapi import HTTPException
    try:service.get(c,'signals',signal['id'])
    except HTTPException as denied:assert denied.status_code==404
    else:raise AssertionError('Cross-workspace evidence became visible')
for table in ('businesses','contact_people','email_messages','workflow_runs'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
print(json.dumps({'live_discovery':'PASSED','database':str(path),'organization_id':org,'job_id':job['id'],'monitor_id':monitor['id'],'signals':len(records),'source_requests':result['items'][0]['result']['requests'],'sample':{'id':signal['id'],'title':signal['title'],'source_url':signal['source_url'],'observed_at':signal['observed_at'],'score':signal['score'],'confidence':signal['evidence']['confidence']},'saved':True,'opportunity':opportunity['id'],'alerts':counts['unread_alerts'],'cross_workspace_denied':True,'lead_engine_or_mail_records_created':0},indent=2))
c.close()
