"""Use existing Git credentials in-memory for gh account/read inspection only."""
import argparse
import json
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gh',required=True)
args=parser.parse_args()
credential=subprocess.run(['git','credential','fill'],cwd=ROOT,input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
if credential.returncode:
    print(json.dumps({'github_api':'BLOCKED','reason':'Existing Git credential helper did not supply a credential; authenticate gh using the authorized owner account.'}));raise SystemExit(1)
values=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
token=values.get('password','')
if not token:raise SystemExit('GitHub CLI authorization unavailable; no credentials printed.')
env={**os.environ,'GH_TOKEN':token}
for command in ([args.gh,'api','user','--jq','{login: .login}'],[args.gh,'repo','view','piyush-agrawal6/AILeadGen','--json','nameWithOwner,defaultBranchRef,isPrivate,url'],[args.gh,'api','repos/piyush-agrawal6/AILeadGen/branches/main','--jq','{name: .name, sha: .commit.sha, protected: .protected}']):
    result=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True)
    if result.returncode:print(json.dumps({'github_api':'BLOCKED','reason':'Owner API permission check failed','exit_code':result.returncode}));raise SystemExit(1)
    print(result.stdout.strip())
