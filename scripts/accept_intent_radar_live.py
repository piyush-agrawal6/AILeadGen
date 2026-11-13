"""Explicit bounded real public HN / existing-gateway acceptance, no customer writes.

This is local transport acceptance, never deployed-runtime or commercial approval.
Only --vertex authorizes spending; source scopes needing approvals are excluded.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime,timezone
from pathlib import Path
from pydantic import BaseModel,Field
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class Probe(BaseModel):
    evidence:str=Field(max_length=120)

async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hn',action='store_true');parser.add_argument('--vertex',action='store_true')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve()
    assert output.is_relative_to(ROOT/'data/artifacts/verification') and output.parent.is_dir()
    result={'at':datetime.now(timezone.utc).isoformat(),'scope':'Local authorized transport; no production/customer writes or grants.','checks':{}}
    if args.hn:
        from app.intent_radar.providers import HackerNews
        try:
            data=await asyncio.wait_for(HackerNews().fetch(feeds=['ask'],limit=3),timeout=25)
            result['checks']['hacker_news']={'status':'PASS','requests':data['requests'],'scanned':data['scanned'],'coverage':data['coverage'],'original_evidence':[{'source_record_id':row['source_record_id'],'source_url':row.get('source_url'),'title':row.get('title'),'observed_at':row.get('observed_at'),'retrieved_at':row.get('retrieved_at')} for row in data['items']]}
        except Exception as exc:result['checks']['hacker_news']={'status':'BLOCKED','error_type':type(exc).__name__}
    if args.vertex:
        os.environ['APP_ENV']='test';os.environ['ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK']='1'
        from app.acquisition import ai
        gateway=ai.provider()
        try:
            data=await asyncio.wait_for(gateway.structured('Return the exact supplied evidence string in the schema. No inference or tool use.',{'evidence':'Local authorized Vertex transport acceptance'},Probe,max_output_tokens=128,timeout_seconds=12),timeout=18)
            result['checks']['vertex']={'status':'PASS' if gateway.last_provider=='VERTEX_AI' and data.evidence=='Local authorized Vertex transport acceptance' else 'VERTEX_NOT_VERIFIED','provider':gateway.last_provider,'model':gateway.last_model,'usage':getattr(gateway,'last_usage',None),'metrics':dict(gateway.metrics),'identity_scope':'Local ADC; deployed service identity not accepted by this probe.'}
        except Exception as exc:result['checks']['vertex']={'status':'BLOCKED','error_type':type(exc).__name__,'metrics':dict(gateway.metrics),'provider_health':gateway.states()}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':asyncio.run(main())
