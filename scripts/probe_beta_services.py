"""Bounded authenticated GETs and one explicitly requested Vertex probe; no mail."""
import argparse,asyncio,hashlib,hmac,json,secrets,subprocess,time
from pathlib import Path
import httpx
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]

def signed_reads(values):
    from app.api.security import canonical_request
    origin='https://leadengine-api-befca7xg4a-el.a.run.app'
    actor=next(value.strip().lower() for value in values['ALLOWED_USER_EMAILS'].split(',') if value.strip())
    result=[]
    with httpx.Client(timeout=20,follow_redirects=False) as client:
        for path in ('/api/organization/workspaces','/api/intent-radar/capabilities','/api/workflow/safety'):
            stamp=str(int(time.time()));nonce=secrets.token_hex(24)
            headers={'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical_request(stamp,nonce,'GET',path,b'',actor).encode(),hashlib.sha256).hexdigest()}
            try:
                response=client.get(origin+path,headers=headers)
                row={'path':path,'http':response.status_code}
                if response.status_code==200 and path.endswith('/workspaces'):
                    body=response.json();row['workspaces']=[{key:item.get(key) for key in ('organization_id','name','role')} for item in body.get('items',[])]
                result.append(row)
            except Exception as error:result.append({'path':path,'error_type':type(error).__name__})
    return result

async def inference():
    from app.acquisition.vertex import VertexAIProvider
    from pydantic import BaseModel,Field
    class Probe(BaseModel):evidence:str=Field(max_length=80)
    provider=VertexAIProvider()
    try:
        result=await asyncio.wait_for(provider.structured('Return only the supplied evidence in the schema.',{'evidence':'PlaneByte authorized beta transport probe'},Probe,max_output_tokens=128,timeout_seconds=12),timeout=25)
        return {'status':'READY' if result.evidence=='PlaneByte authorized beta transport probe' else 'INVALID_OUTPUT','model':provider.model,'identity_scope':'Local ADC; not deployed runtime acceptance.','usage':getattr(provider,'last_usage',None)}
    except Exception as error:return {'status':'BLOCKED','error_type':type(error).__name__,'identity_scope':'Local ADC only; no Gemini fallback attempted.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--vertex',action='store_true');args=parser.parse_args()
    values=dotenv_values(ROOT/'.env');result={'signed_backend_reads':signed_reads(values)}
    if args.vertex:result['vertex']=asyncio.run(inference())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
