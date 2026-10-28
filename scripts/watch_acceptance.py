"""Observe one existing acceptance campaign; never create or resume work."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.live_acceptance import call

path=Path('docs/production-acceptance-scan.json')
state=json.loads(path.read_text(encoding='utf-8'));cid=state['campaign_id'];last_id=0
deadline=time.monotonic()+3600
while time.monotonic()<deadline:
    try:
        campaign=call('GET','/api/campaigns/'+cid).json()
        rid=campaign['runs'][0]['id']
        events=call('GET',f'/api/scans/{rid}/events?after_id={last_id}&limit=1000').json()
        for event in events:
            last_id=max(last_id,event['id'])
            print(event['timestamp'],event['stage'],event['message'],flush=True)
        state['latest_campaign']=campaign;state['checked_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        if campaign['status']=='COMPLETED':
            state['results']=call('GET','/api/intelligence/leads?campaign='+cid+'&page_size=100').json()
        path.write_text(json.dumps(state,indent=2),encoding='utf-8')
        if campaign['status'] not in ['RUNNING','QUEUED']:
            print(json.dumps({'status':campaign['status'],'counters':campaign['counters'],'runs':campaign['runs']}),flush=True)
            break
    except Exception as exc:
        print('Transient monitor error:',type(exc).__name__,flush=True)
    time.sleep(30)
else:raise SystemExit('Monitoring deadline reached; inspect the existing campaign before taking further action.')
