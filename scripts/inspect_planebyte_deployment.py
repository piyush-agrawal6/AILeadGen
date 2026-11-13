"""Read-only deployment account/configuration inspection with secret redaction."""
import json
import subprocess
import httpx

def command(*args):return json.loads(subprocess.check_output(args,text=True))
project=command('vercel','api','/v9/projects/leadengine')
print(json.dumps({'vercel':{key:project.get(key) for key in ('id','name','rootDirectory','framework','nodeVersion','buildCommand','installCommand','link','ssoProtection')}} ,indent=2))
domains=command('vercel','api','/v9/projects/leadengine/domains')
print(json.dumps({'project_domains':[{k:domain.get(k) for k in ('name','verified','redirect','gitBranch')} for domain in domains.get('domains',[])]},indent=2))
service=command('gcloud','run','services','describe','leadengine-api','--region','asia-south1','--project','querryside','--format=json')
spec=service['spec']['template']['spec']
env={entry['name']:entry for entry in spec['containers'][0].get('env',[])}
public=['APP_ENV','INTENT_RADAR_STAGE','INTENT_RADAR_AI_ENABLED','INTENT_RADAR_SCHEDULES_ENABLED','INTENT_RADAR_STACKEXCHANGE_ENABLED','HEYSOW_MCP_ENABLED','HEYSOW_DEVELOPER_API_ENABLED']
print(json.dumps({'cloud_run':{'url':service['status']['url'],'latest_ready_revision':service['status'].get('latestReadyRevisionName'),'service_identity':spec.get('serviceAccountName'),'configuration_names':sorted(env),'gates':{key:env.get(key,{}).get('value','Absent or secret-managed') for key in public},'secret_managed_names':sorted(key for key,value in env.items() if 'valueFrom' in value),'database_url_present':'DATABASE_URL' in env}},indent=2))
environments=command('vercel','api','/v10/projects/leadengine/env')
print(json.dumps({'vercel_environment_presence':[{'name':entry['key'],'targets':entry.get('target',[]),'configured':True} for entry in environments.get('envs',[])]},indent=2))
for origin in ('https://app.planebyte.com',service['status']['url']+'/api/health'):
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as client:response=client.get(origin)
        print(json.dumps({'endpoint':origin,'status':response.status_code,'redirect':response.headers.get('location'),'tls_verified':True}))
    except Exception as exc:print(json.dumps({'endpoint':origin,'error_type':type(exc).__name__,'tls_verified':False}))
