"""The production guard must reject stale bundles before the Vercel build."""
import json,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
NODE=Path('/Users/planebyte/Documents/Projects/planebyte-leadgen/data/artifacts/runtime/node-v24.22.2-darwin-x64/bin/node')
@pytest.mark.parametrize('case,passes',[('missing',False),('wrong-branch',False),('missing-ai',False),('verified',True)])
def test_production_bundle_requires_integrated_source(tmp_path,case,passes):
 if not NODE.exists():pytest.skip('Established Node24 runtime is unavailable')
 policy=json.loads((ROOT/'dashboard/release-policy.json').read_text());(tmp_path/'release-policy.json').write_text(json.dumps(policy));(tmp_path/'public').mkdir()
 manifest={k:policy[k] for k in ('branch','ui_baseline','backend_baseline')};manifest.update(source_commit='a'*40,frontend_tree='b'*40)
 if case=='wrong-branch':manifest['branch']='main'
 if case=='missing-ai':manifest['backend_baseline']='c'*40
 if case!='missing':(tmp_path/'public/release.json').write_text(json.dumps(manifest))
 run=subprocess.run([str(NODE),str(ROOT/'dashboard/scripts/verify-production-source.mjs'),'--require'],cwd=tmp_path,capture_output=True,text=True)
 assert (run.returncode==0)==passes
