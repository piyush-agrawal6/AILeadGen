"""Verify one approved source package; leave the prepared candidate intact."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
from prepare_frontend_release import prepare,git

def check(destination,deployed_source):
    manifest=prepare(destination,deployed_source);root=destination/'dashboard'
    if (manifest['source_commit'],manifest['frontend_tree'])!=(git('rev-parse','HEAD'),git('rev-parse','HEAD:dashboard')):raise RuntimeError('Candidate identity mismatch')
    cmd=['node','scripts/verify-production-source.mjs','--require'];subprocess.run(cmd,cwd=root,check=True)
    with tempfile.TemporaryDirectory() as d:
        scratch=Path(d);(scratch/'public').mkdir();(scratch/'scripts').mkdir()
        for path in ('release-policy.json','scripts/verify-production-source.mjs'):shutil.copy2(root/path,scratch/path)
        (scratch/'public/release.json').write_text(json.dumps(dict(manifest,branch='deliberately-unapproved')))
        negative=subprocess.run(cmd,cwd=scratch,capture_output=True,text=True)
        if negative.returncode==0 or 'not the prepared integrated release' not in negative.stderr:raise RuntimeError('Expected original verifier to reject a branch mismatch')
    print('Negative branch control rejected; package:',destination)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',required=True,type=Path);p.add_argument('--deployed-source',required=True);a=p.parse_args();check(a.destination.resolve(),a.deployed_source)
