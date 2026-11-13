"""Read-only existing deployment/DB inspection; never print credential values."""
import json,subprocess
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
def command(*args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=60,cwd=ROOT)
    if result.returncode:raise RuntimeError('AUTHORIZATION_OR_COMMAND_UNAVAILABLE')
    return json.loads(result.stdout)

def database(url):
    import psycopg
    result={'configured':bool(url),'scope':'Read-only metadata; no migration or customer writes.'}
    if not url:return result
    try:
        with psycopg.connect(url,connect_timeout=10,autocommit=True) as c:
            c.execute('BEGIN READ ONLY');c.execute('SET LOCAL statement_timeout=5000')
            result.update(connected=True,read_only=c.execute('SHOW transaction_read_only').fetchone()[0]=='on',version=c.execute('SHOW server_version').fetchone()[0])
            if c.execute("SELECT to_regclass('schema_migrations')").fetchone()[0]:result['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
            tables={name for name, in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('organizations','organization_products','organization_onboarding')").fetchall()}
            if 'organizations' in tables:result['workspaces']=[{'id':row[0],'name':row[1],'status':row[2]} for row in c.execute('SELECT id,name,status FROM organizations ORDER BY id LIMIT 20').fetchall()]
            if 'organization_products' in tables:result['radar_grants']=[{'organization_id':row[0],'enabled':bool(row[1])} for row in c.execute("SELECT organization_id,enabled FROM organization_products WHERE product='INTENT_RADAR' ORDER BY organization_id LIMIT 50").fetchall()]
            if 'organization_onboarding' in tables:result['onboarding']=[{'organization_id':row[0],'status':row[1]} for row in c.execute('SELECT organization_id,status FROM organization_onboarding ORDER BY organization_id LIMIT 50').fetchall()]
    except Exception as error:result.update(connected=False,error_type=type(error).__name__)
    return result

def main():
    result={};local=dotenv_values(ROOT/'.env',interpolate=False)
    try:
        project=command('vercel','api','/v9/projects/leadengine');team=command('vercel','api','/v2/teams/'+project['accountId'])
        deployments=command('vercel','api','/v6/deployments?projectId='+project['id']+'&limit=3')
        result['vercel']={'project':project['name'],'root_directory':project.get('rootDirectory'),'git_link_configured':bool(project.get('link')),'node':project.get('nodeVersion'),'plan':team.get('billing',{}).get('plan'),'deployments':[{key:row.get(key) for key in ('uid','url','state','target','created','source')} for row in deployments.get('deployments',[])]}
    except Exception as error:result['vercel']={'error_type':type(error).__name__}
    try:
        service=command('gcloud','run','services','describe','leadengine-api','--project','querryside','--region','asia-south1','--format=json')
        spec=service['spec']['template']['spec'];env={item['name']:item for item in spec['containers'][0].get('env',[])}
        result['backend']={'url':service['status']['url'],'revision':service['status'].get('latestReadyRevisionName'),'identity':spec.get('serviceAccountName'),'image':spec['containers'][0]['image']}
        def value(name):
            row=env.get(name,{})
            if 'value' in row:return row['value']
            ref=row.get('valueFrom',{}).get('secretKeyRef')
            if not ref:return ''
            response=subprocess.run(['gcloud','secrets','versions','access',ref['key'],'--secret',ref['name'],'--project','querryside'],capture_output=True,text=True,timeout=30)
            if response.returncode:raise RuntimeError('SECRET_ACCESS_UNAVAILABLE')
            return response.stdout
        for name in ('DATABASE_URL','LEADENGINE_API_SIGNING_SECRET'):
            try:
                secret=value(name)
                result[name]={'runtime_present':bool(secret),'matches_local':bool(secret and secret==local.get(name))}
                if name=='DATABASE_URL':result['database']=database(secret)
            except Exception as error:result[name]={'error_type':type(error).__name__}
        jobs=command('gcloud','run','jobs','list','--project','querryside','--region','asia-south1','--format=json')
        result['jobs']=[{'name':job['metadata']['name'],'identity':job.get('spec',{}).get('template',{}).get('spec',{}).get('template',{}).get('spec',{}).get('serviceAccountName')} for job in jobs]
        scheduled=command('gcloud','scheduler','jobs','list','--project','querryside','--location','asia-south1','--format=json')
        result['schedulers']=[{'name':job['name'].rsplit('/',1)[-1],'state':job.get('state'),'schedule':job.get('schedule'),'timezone':job.get('timeZone'),'target':job.get('httpTarget',{}).get('uri'),'identity':(job.get('httpTarget',{}).get('oauthToken') or job.get('httpTarget',{}).get('oidcToken') or {}).get('serviceAccountEmail')} for job in scheduled]
    except Exception as error:result['cloud_inventory_error']={'error_type':type(error).__name__}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
