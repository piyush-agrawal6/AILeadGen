"""Bounded mixed authenticated read measurements; no provider/job execution.

Observed sample percentiles are not population SLAs or a cold-start claim.
Concurrency is capped at four; source health reads persisted metadata only.
"""
import argparse,concurrent.futures,json,math,statistics,time
from pathlib import Path
import httpx
from scripts.deploy_product_release import signed,ROOT

PATHS=('/api/intent-radar/overview/summary','/api/intent-radar/overview','/api/intent-radar/signals?page_size=20','/api/intent-radar/opportunities?page_size=20','/api/intent-radar/saved?page_size=20','/api/intent-radar/growth/overview?days=0','/api/organization/usage','/api/intent-radar/settings','/api/organization/workspaces','/api/intent-radar/sources/health')
ORIGINS=('https://leadengine-api-befca7xg4a-el.a.run.app','https://intent-only---leadengine-api-befca7xg4a-el.a.run.app')

def main():
    p=argparse.ArgumentParser();p.add_argument('--staged',action='store_true');p.add_argument('--samples',type=int,choices=range(1,11),default=10);p.add_argument('--concurrency',type=int,choices=range(1,5),default=2);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    origin=ORIGINS[int(args.staged)];results=[]
    with httpx.Client(base_url=origin,timeout=90,follow_redirects=False,limits=httpx.Limits(max_connections=args.concurrency,max_keepalive_connections=args.concurrency)) as client:
        def request(item):
            sample,path=item;started=time.monotonic();row={'path':path,'sample':sample+1}
            try:
                r=signed(client,path);row.update(status=r.status_code,server_timing=r.headers.get('server-timing'),cache=r.headers.get('x-le-cache'))
            except httpx.HTTPError as error:row.update(status=None,error_type=type(error).__name__)
            row['seconds']=round(time.monotonic()-started,4);return row
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for row in pool.map(request,[(i,path) for i in range(args.samples) for path in PATHS]):
                results.append(row);print(json.dumps(row),flush=True)
    summary=[]
    for path in PATHS:
        rows=[r for r in results if r['path']==path];x=sorted(r['seconds'] for r in rows)
        summary.append({'path':path,'samples':len(x),'p50_seconds':statistics.median(x),'p95_observed_seconds':x[math.ceil(len(x)*.95)-1],'failures':sum(r['status']!=200 for r in rows)})
    data={'origin':origin,'concurrency':args.concurrency,'sampling':'Bounded mixed owner-workspace reads from the operator machine. No proven cold start, population SLA or broad customer-scale claim. No external-source fetch or AI operation.','results':results,'summary':summary}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2));args.output.chmod(0o600)
    print(json.dumps({'read_samples':len(results),'concurrency':args.concurrency,'summary':summary}))
if __name__=='__main__':main()
