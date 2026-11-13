"""Set only approved noncredential production UI capabilities in existing Vercel.

OAuth/session/API credentials, subscription, domains and hosting are untouched.
Values stay sensitive if Vercel stores them that way; no declassification.
"""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM='team_wYIkjGUus2DtSgRualzW0kge';PROJECT='prj_xT1PDDXHTYsjdHgI776MQtLzFPZb'
FLAGS={key:'true' for key in ('HEYSOW_WORKSPACE_MANAGEMENT_ENABLED','HEYSOW_COMPANY_DISCOVERY_ENABLED','HEYSOW_COMPANY_AI_ENABLED','HEYSOW_ICP_AI_ENABLED','HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED','HEYSOW_LEAD_ASSISTANT_ENABLED','HEYSOW_DEVELOPER_API_ENABLED')}
FLAGS.update({key:'false' for key in ('HEYSOW_PUBLIC_REGISTRATION_ENABLED','HEYSOW_INVITED_REGISTRATION_ENABLED','HEYSOW_CUSTOMER_ACCESS_ENABLED')})

def cli(args,data=None):
    result=subprocess.run(['vercel',*args,'--scope=piyushagrawal6s-projects'],cwd=ROOT/'dashboard',input=data,text=True,capture_output=True,timeout=90)
    if result.returncode:raise RuntimeError('Vercel command failed; no credentials were printed: '+' '.join(args[:3]))
    return result.stdout

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    rows=json.loads(cli(['api','/v10/projects/'+PROJECT+'/env?teamId='+TEAM]))['envs']
    production={row['key']:row for row in rows if 'production' in row.get('target',[])}
    output={}
    for key,value in FLAGS.items():
        row=production.get(key)
        if row and set(row.get('target',[]))!={'production'}:raise RuntimeError('A shared multi-environment record requires a scoped split before updating: '+key)
        output[key]={'present':bool(row),'storage':row.get('type') if row else None,'expected':value}
        if args.apply:
            cli(['env','update' if row else 'add',key,'--environment=production','--sensitive','--yes'],data=value)
            output[key]['applied']=True
    artifact=ROOT/'data/artifacts/verification'/('phase4-vercel-ui-flags-applied.json' if args.apply else 'phase4-vercel-ui-flags-inspected.json')
    artifact.write_text(json.dumps({'project':PROJECT,'changes_applied':args.apply,'flags':output,'credentials_changed':False},indent=2));artifact.chmod(0o600)
    print(json.dumps({'changes_applied':args.apply,'flags':output,'credentials_changed':False}))
if __name__=='__main__':main()
