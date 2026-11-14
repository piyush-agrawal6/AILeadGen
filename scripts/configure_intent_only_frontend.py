"""Set the one reversible availability flag in the existing Vercel project.

No OAuth credentials, other flags, domains, Git configuration or plan changes.
"""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=ROOT/'data/artifacts/runtime/node-v24.22.2-darwin-x64/bin/node'
CLI=Path('/Users/planebyte/.nvm/versions/node/v26.13.0/bin/vercel')
PROJECT='prj_xT1PDDXHTYsjdHgI776MQtLzFPZb';TEAM='team_wYIkjGUus2DtSgRualzW0kge'
def cli(args,data=None):
    p=subprocess.run([str(NODE),str(CLI),*args,'--scope=piyushagrawal6s-projects'],cwd=ROOT/'dashboard',input=data,text=True,capture_output=True,timeout=120)
    if p.returncode:raise RuntimeError('Existing-project Vercel configuration failed; private response withheld.')
    return p.stdout

def main():
    rows=json.loads(cli(['api','/v10/projects/'+PROJECT+'/env?teamId='+TEAM]))['envs']
    matching=[row for row in rows if row['key']=='LEAD_ENGINE_AVAILABLE' and 'production' in row.get('target',[])]
    if len(matching)>1 or matching and set(matching[0]['target'])!={'production'}:raise RuntimeError('Availability requires a single production-scoped environment record.')
    cli(['env','update' if matching else 'add','LEAD_ENGINE_AVAILABLE','--environment=production','--sensitive','--yes'],data='false')
    proof={'project':PROJECT,'production_flag':'LEAD_ENGINE_AVAILABLE=false','other_environment_changed':False,'credentials_changed':False,'domains_changed':False}
    p=ROOT/'data/artifacts/verification/intent-only/vercel-availability.json';p.write_text(json.dumps(proof,indent=2));p.chmod(0o600);print(json.dumps(proof))
if __name__=='__main__':main()
