"""One real, grounded analysis of previously fetched evidence in a disposable DB."""
import argparse,asyncio,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.platform.context import workspace_scope
from app.intent_radar import intelligence,models,service
from app.icp import service as icps,models as icp_models

async def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--local-token-limit',type=int,default=60000);args=p.parse_args()
    path=Path(args.database).resolve();base=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
    assert path.is_file() and path.is_relative_to(base)
    os.environ['ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK']='1'
    s=get_settings();s.app_env='test';s.database_path=str(path);s.database_url='';s.intent_radar_stage='Beta';s.intent_radar_ai_enabled=True;s.allowed_user_emails='radar23@example.test'
    assert 60000<=args.local_token_limit<=180000
    s.intent_radar_ai_daily_tokens=args.local_token_limit
    c=get_connection(path);owner=c.execute("SELECT id,created_by_user_id FROM organizations WHERE name='Disposable Radar 23 acceptance'").fetchone();assert owner
    with workspace_scope(c,owner['created_by_user_id'],owner['id']):
        row=c.execute("SELECT id FROM intent_signals WHERE organization_id=? AND source='Hacker News' AND category='Recommendation request' AND available=1 ORDER BY score DESC LIMIT 1",(owner['id'],)).fetchone()
        if not row:row=c.execute("SELECT id FROM intent_signals WHERE organization_id=? AND source='Hacker News' AND available=1 LIMIT 1",(owner['id'],)).fetchone()
        assert row
        icp=icps.create(c,icp_models.Create(name='Software services research',criteria=icp_models.Criteria(intent=icp_models.IntentCriteria(relevant_services=['custom software development','software engineering consulting'])),request_id=uuid.uuid4()));c.commit()
        result=await intelligence.analyze(c,row['id'],models.AnalysisRequest(icp_id=icp['id']));c.commit()
        repeat=await intelligence.analyze(c,row['id'],models.AnalysisRequest(icp_id=icp['id']))
        signal=service.get(c,'signals',row['id'])
        print(json.dumps({'source':{'title':signal['title'],'url':signal['source_url']},'analysis':result,'repeat_cached':repeat['cached'],'no_external_actions':True},indent=2))
    c.close()
if __name__=='__main__':asyncio.run(main())
