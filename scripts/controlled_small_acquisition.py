"""One bounded five-lead manual production scan; flags remain false. No mail."""
import sys,json,time,hmac,hashlib,secrets,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from dotenv import dotenv_values
p=argparse.ArgumentParser();p.add_argument('--start',action='store_true');a=p.parse_args();v=dotenv_values('.env');actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower()
record_path=Path('docs/controlled-small-acquisition.json');record=json.loads(record_path.read_text()) if record_path.exists() else {}
def call(method,path,payload=None):
 body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b'';stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 canonical='\n'.join([stamp,nonce,method,path,hashlib.sha256(body).hexdigest(),actor])
 headers={'Content-Type':'application/json','X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(v['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
 r=requests.request(method,'https://leadengine-api-befca7xg4a-el.a.run.app'+path,data=body or None,headers=headers,timeout=120)
 if r.status_code not in (200,201):raise SystemExit('Controlled scan request failed HTTP '+str(r.status_code))
 return r.json()
summary=call('GET','/api/automation/summary')
assert not any(summary['environment'][key] for key in ('scan_enabled','auto_email_enabled','sending_enabled'))
if a.start and not record.get('run_id'):
 # Target five is the deployed API's smallest permitted target; reuse normal production pipeline.
 r=call('POST','/api/scans',{'market':'Bristol, United Kingdom','vertical':'dentists','target':5,'settings':{'exclude_chains':True,'lighthouse_enabled':False,'overture_enabled':False,'osm_enabled':True,'max_pages':3,'page_timeout':8,'site_timeout':20,'http_concurrency':3,'crawler_concurrency':2,'min_score':35}})
 record={'run_id':r['run_id'],'target':5,'mail_enabled':False,'method':'existing manual scan API and production discovery pipeline'};record_path.write_text(json.dumps(record,indent=2))
if record.get('run_id'):
 r=call('GET','/api/scans/'+str(record['run_id']));record['scan']={k:r.get(k) for k in ('status','raw_found','deduped','filtered','websites_processed','qualified','exported','started_at','finished_at')};record_path.write_text(json.dumps(record,indent=2));print(json.dumps(record))
