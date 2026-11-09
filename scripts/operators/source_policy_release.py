"""Image-only source-policy release: preserve environment, infrastructure and data."""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.stage_acquisition_release import command,runtime,digest,REGION
STATE=Path('deploy/source-policy-release.json')

def stable_spec(value):
 result=copy.deepcopy(value)
 result.get('template',{}).get('metadata',{}).get('labels',{}).pop('client.knative.dev/nonce',None)
 return result

def stage(build_id):
 build=command(['builds','describe',build_id,'--region='+REGION]);assert build['status']=='SUCCESS','Exact-lock Linux tests must pass first'
 images=build['images'];api_image=next(x for x in images if '/api:' in x);source_image=next(x for x in images if '/acquisition:' in x);maps_image=next(x for x in images if '/worker:' in x)
 api,api_spec=runtime(True);maps,maps_spec=runtime(False);source=command(['run','jobs','describe','leadengine-acquisition','--region='+REGION]);source_spec=source['spec']['template']['spec']['template']['spec']
 before={'api_env':api_spec['containers'][0].get('env',[]),'maps_spec':maps['spec'],'source_spec':source['spec']}
 # These private rollback specifications contain only existing secret references.
 rollback=Path('/private/tmp/leadengine-source-policy-rollback.json');
 if not rollback.exists():rollback.write_text(json.dumps({'api':api,'maps':maps,'source':source}));rollback.chmod(0o600)
 command(['run','jobs','update','leadengine-acquisition','--region='+REGION,'--image='+source_image,'--quiet'])
 command(['run','services','update','leadengine-api','--region='+REGION,'--image='+api_image,'--no-traffic','--quiet'])
 new_api,new_api_spec=runtime(True);assert new_api_spec['containers'][0].get('env',[])==before['api_env']
 new_source=command(['run','jobs','describe','leadengine-acquisition','--region='+REGION]);expected=copy.deepcopy(before['source_spec']);expected['template']['spec']['template']['spec']['containers'][0]['image']=source_image;assert stable_spec(new_source['spec'])==stable_spec(expected)
 revision=new_api['status']['latestCreatedRevisionName'];check=command(['run','revisions','describe',revision,'--region='+REGION]);assert any(x['type']=='Ready' and x['status']=='True' for x in check['status']['conditions'])
 STATE.write_text(json.dumps({'build_id':build_id,'api_image':api_image,'source_image':source_image,'maps_image':maps_image,'previous_api_revision':api['status']['latestReadyRevisionName'],'staged_revision':revision,'maps_spec_sha_before':digest(before['maps_spec']),'environment_preserved':True,'production_promoted':False},indent=2))
 print(json.dumps({'staged_revision':revision,'environment_preserved':True,'maps_worker_unchanged':digest(runtime(False)[0]['spec'])==digest(before['maps_spec'])}))

def promote(preserve_maps=False):
 state=json.loads(STATE.read_text());maps,_=runtime(False);assert digest(maps['spec'])==state['maps_spec_sha_before']
 before=copy.deepcopy(maps['spec'])
 # Existing executions keep their immutable image; only future executions change.
 if not preserve_maps:
  command(['run','jobs','update','leadengine-worker','--region='+REGION,'--image='+state['maps_image'],'--quiet'])
  updated,_=runtime(False);expected=copy.deepcopy(before);expected['template']['spec']['template']['spec']['containers'][0]['image']=state['maps_image'];assert stable_spec(updated['spec'])==stable_spec(expected)
 else:
  updated=maps;state['built_maps_image']=state['maps_image'];state['maps_image']=before['template']['spec']['template']['spec']['containers'][0]['image']
 command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+state['staged_revision']+'=100','--quiet'])
 state.update(production_promoted=True,maps_spec_sha_after=digest(updated['spec']),worker_environment_resources_preserved=True,no_execution_cancelled=True,no_migration_run=True)
 STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':state['staged_revision'],'future_worker_image_updated':not preserve_maps,'environment_preserved':True,'no_migrations_or_execution_cancellations':True}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','promote']);p.add_argument('--build');p.add_argument('--preserve-maps',action='store_true');a=p.parse_args();stage(a.build) if a.action=='stage' else promote(a.preserve_maps)
