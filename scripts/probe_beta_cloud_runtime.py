"""Explicit read-only probe on the existing attached worker identity, no job edit."""
import argparse,json
from app.cloud_doctor import authorized_session

CODE=r'''
import os,json
result={'scope':'Existing worker execution; read-only database and one bounded Vertex request.'}
try:
 import psycopg
 with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=10,autocommit=True) as c:
  c.execute('BEGIN READ ONLY');c.execute('SET LOCAL statement_timeout=5000')
  result['database']={'connected':True,'read_only':c.execute('SHOW transaction_read_only').fetchone()[0]=='on','version':c.execute('SHOW server_version').fetchone()[0]}
  tables={row[0] for row in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('schema_migrations','organizations','organization_products','organization_onboarding')").fetchall()}
  if 'schema_migrations' in tables:result['database']['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
  if 'organizations' in tables:result['database']['workspaces']=[{'id':row[0],'name':row[1],'status':row[2]} for row in c.execute('SELECT id,name,status FROM organizations ORDER BY id LIMIT 20').fetchall()]
  if 'organization_products' in tables:result['database']['radar_grants']=[{'organization_id':row[0],'enabled':bool(row[1])} for row in c.execute("SELECT organization_id,enabled FROM organization_products WHERE product='INTENT_RADAR' LIMIT 50").fetchall()]
except Exception as error:
 text=str(error).lower()
 reason='DNS' if 'translate host' in text or 'resolve' in text else 'AUTH' if 'password authentication' in text or 'authentication failed' in text else 'SUSPENDED_ENDPOINT' if 'endpoint is disabled' in text or 'endpoint has been disabled' in text else 'NETWORK_TIMEOUT' if 'timeout' in text or 'timed out' in text else 'TLS' if 'ssl' in text or 'certificate' in text else 'CONNECTION_UNAVAILABLE'
 result['database']={'connected':False,'error_type':type(error).__name__,'failure_class':reason,'sqlstate':getattr(error,'sqlstate',None)}
 if os.getenv('PLANEBYTE_BETA_DATABASE_ONLY')=='1':
  import socket
  from urllib.parse import urlsplit
  target=urlsplit(os.environ['DATABASE_URL']);checks=[]
  for family,kind,proto,_,address in socket.getaddrinfo(target.hostname,target.port or 5432,type=socket.SOCK_STREAM)[:2]:
   try:
    with socket.socket(family,kind,proto) as stream:stream.settimeout(3);stream.connect(address)
    checks.append({'family':'IPv6' if family==socket.AF_INET6 else 'IPv4','tcp':'CONNECTED'})
   except Exception as probe:checks.append({'family':'IPv6' if family==socket.AF_INET6 else 'IPv4','tcp':type(probe).__name__})
  result['database']['network_checks']=checks
if os.getenv('PLANEBYTE_BETA_DATABASE_ONLY')=='1':
 print('PLANEBYTE_BETA_RUNTIME_PROBE='+json.dumps(result));raise SystemExit(0)
try:
 import google.auth,requests
 from google.auth.transport.requests import Request
 class Bounded(Request):
  def __call__(self,*args,**kwargs):kwargs['timeout']=10;return super().__call__(*args,**kwargs)
 credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform']);credentials.refresh(Bounded())
 project=os.environ['VERTEX_AI_PROJECT_ID'];location=os.environ['VERTEX_AI_LOCATION'];model=os.environ['VERTEX_AI_MODEL'];host='aiplatform.googleapis.com' if location=='global' else location+'-aiplatform.googleapis.com'
 response=requests.post('https://'+host+'/v1/projects/'+project+'/locations/'+location+'/publishers/google/models/'+model+':generateContent',headers={'Authorization':'Bearer '+credentials.token,'x-goog-user-project':project},json={'contents':[{'role':'user','parts':[{'text':'Reply only with JSON {"ready":true}.'}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':128}},timeout=12)
 result['vertex']={'http':response.status_code,'model':model,'identity':'Existing attached worker service account','fallback_attempted':False}
 if response.status_code==200:
  body=response.json();text=''.join(part.get('text','') for item in body.get('candidates',[]) for part in item.get('content',{}).get('parts',[]) if not part.get('thought'));result['vertex']['valid_json']=json.loads(text).get('ready') is True;result['vertex']['usage']=body.get('usageMetadata',{})
except Exception as error:result['vertex']={'error_type':type(error).__name__,'fallback_attempted':False}
print('PLANEBYTE_BETA_RUNTIME_PROBE='+json.dumps(result))
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--database-only',action='store_true');args=parser.parse_args()
    if not args.execute:
        print(json.dumps({'mode':'dry-run','job':'leadengine-worker','database':'Read-only session','vertex_requests':1,'mail_or_scans':False,'job_configuration_changed':False}));return
    session=authorized_session()
    response=session.post('https://run.googleapis.com/v2/projects/querryside/locations/asia-south1/jobs/leadengine-worker:run',json={'overrides':{'taskCount':1,'timeout':'60s','containerOverrides':[{'args':['python','-c',CODE],'env':[{'name':key,'value':'false'} for key in ('EMAIL_SENDING_ENABLED','AUTO_EMAIL_ENABLED','AUTO_SCAN_ENABLED','EMAIL_SYNC_ENABLED')]+[{'name':'PLANEBYTE_BETA_DATABASE_ONLY','value':'1' if args.database_only else '0'}]}]}},timeout=30)
    if response.status_code>=400:print(json.dumps({'dispatched':False,'http':response.status_code}));return
    body=response.json();print(json.dumps({'dispatched':True,'operation':body.get('name'),'execution':body.get('metadata',{}).get('name'),'job_configuration_changed':False}))
if __name__=='__main__':main()
