"""Ordered, source-only feature rollout. Existing scan/mail flags are immutable here."""
import sys,json,re,argparse,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.stage_acquisition_release import command,runtime,digest,REGION,STATE
from app.database.connection import get_connection
os.environ['DATABASE_BACKEND']='postgres'
FLAGS=['ENABLE_AI_ACQUISITION','ENABLE_FIRECRAWL_ACQUISITION','ENABLE_LEAD_IMPORT','ENABLE_GOOGLE_SHEETS_IMPORT']
def enable(flag):
 assert flag in FLAGS
 state=json.loads(STATE.read_text());assert digest(runtime(False)[0]['spec'])==state['existing_worker_spec_sha256']
 before,api=runtime(True);original=api['containers'][0]['env'];plain={e['name']:e.get('value') for e in original}
 assert all(plain.get(k)=='true' for k in FLAGS[:FLAGS.index(flag)]),'Earlier source features must pass and enable first'
 if flag=='ENABLE_AI_ACQUISITION':
  c=get_connection(session_bound=True)
  try:
   row=c.execute("SELECT status,checked_at FROM acquisition_provider_health WHERE provider='gemini'").fetchone();assert row and row['status']=='HEALTHY','Production structured-output check must pass'
  finally:c.close()
 job=command(['run','jobs','describe','leadengine-acquisition','--region='+REGION]);jobenv=job['spec']['template']['spec']['template']['spec']['containers'][0]['env']
 command(['run','jobs','update','leadengine-acquisition','--region='+REGION,'--update-env-vars='+flag+'=true','--quiet'])
 command(['run','services','update','leadengine-api','--region='+REGION,'--update-env-vars='+flag+'=true','--no-traffic','--quiet'])
 d,new=runtime(True);assert sorted([e for e in original if e['name']!=flag],key=lambda e:e['name'])==sorted([e for e in new['containers'][0]['env'] if e['name']!=flag],key=lambda e:e['name'])
 j=command(['run','jobs','describe','leadengine-acquisition','--region='+REGION]);newjob=j['spec']['template']['spec']['template']['spec']['containers'][0]['env'];assert sorted([e for e in jobenv if e['name']!=flag],key=lambda e:e['name'])==sorted([e for e in newjob if e['name']!=flag],key=lambda e:e['name'])
 revision=d['status']['latestCreatedRevisionName'];r=command(['run','revisions','describe',revision,'--region='+REGION]);assert any(x['type']=='Ready' and x['status']=='True' for x in r['status']['conditions'])
 command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100','--quiet']);assert digest(runtime(False)[0]['spec'])==state['existing_worker_spec_sha256']
 p=Path('.env');s=p.read_text();assert len(re.findall('^'+flag+'=',s,re.M))==1;p.write_text(re.sub('^'+flag+'=.*$',flag+'=true',s,flags=re.M))
 state['promoted_revision']=revision;state.setdefault('enabled_source_features',[])
 if flag not in state['enabled_source_features']:state['enabled_source_features'].append(flag)
 state['new_features_enabled']=len(state['enabled_source_features'])==len(FLAGS);STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'enabled_source_feature':flag,'revision':revision,'existing_scan_mail_worker_preserved':True,'no_outreach_or_scan_started':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('flag',choices=FLAGS);args=p.parse_args();enable(args.flag)
