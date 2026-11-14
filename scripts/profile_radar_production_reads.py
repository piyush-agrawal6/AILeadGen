"""Bounded authenticated read latency samples; never starts jobs or providers."""
import argparse,hashlib,hmac,json,statistics,time,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
BASE='https://leadengine-api-befca7xg4a-el.a.run.app'
PATHS=('/api/intent-radar/overview','/api/intent-radar/sources/health','/api/intent-radar/opportunities?page_size=20','/api/intent-radar/saved?page_size=20')

def main():
    p=argparse.ArgumentParser();p.add_argument('--samples',type=int,choices=range(1,11),default=3);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    secret=dotenv_values(ROOT/'.env',interpolate=False).get('LEADENGINE_API_SIGNING_SECRET')
    if not secret:raise SystemExit('Server signing configuration missing; no request sent.')
    actor='planebyte@gmail.com';results=[]
    with httpx.Client(timeout=httpx.Timeout(85,connect=5),follow_redirects=False) as client:
        for path in PATHS:
            for sample in range(args.samples):
                stamp=str(int(time.time()));nonce=uuid.uuid4().hex
                canonical='\n'.join((stamp,nonce,'GET',path,hashlib.sha256(b'').hexdigest(),actor))
                headers={'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-user':actor,'x-le-signature':hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()}
                started=time.monotonic();item={'path':path,'sample':sample+1}
                try:
                    response=client.get(BASE+path,headers=headers)
                    item.update(status=response.status_code,server_timing=response.headers.get('server-timing',''),cache=response.headers.get('x-le-cache',''))
                except httpx.HTTPError as error:item.update(status=None,error=type(error).__name__)
                item['seconds']=round(time.monotonic()-started,3);results.append(item)
                print(json.dumps(item),flush=True)
    summary=[]
    for path in PATHS:
        rows=[r for r in results if r['path']==path];values=sorted(r['seconds'] for r in rows)
        summary.append({'path':path,'samples':len(rows),'median_seconds':statistics.median(values),'p95_observed_seconds':values[max(0,__import__('math').ceil(len(values)*.95)-1)],'failed':sum(r.get('status')!=200 for r in rows)})
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'origin':BASE,'read_only_operations':True,'sampling':'Small sequential production sample; not a load or scalability certification.','results':results,'summary':summary},indent=2));args.output.chmod(0o600)
if __name__=='__main__':main()
