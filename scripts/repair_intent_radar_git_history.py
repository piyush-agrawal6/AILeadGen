"""Reconstruct only the single private commit, retaining source and recovery refs.

Dry-run by default. Does not push, reset the worktree, change remote history,
delete archives or change Git configuration. Requires the exact known baseline.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMP=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
def git(*arguments,env=None,input=None):
    return subprocess.check_output(['git',*arguments],cwd=ROOT,env=env,input=input)
head=git('rev-parse','HEAD').decode().strip()
base=git('rev-parse','origin/main').decode().strip()
assert git('branch','--show-current').decode().strip()=='main'
assert head=='f9350a8a4ddf4dd3ed445b68462274b9bf62e50d'
assert git('rev-list','--parents','-n','1',head).decode().split()==[head,base]
assert git('rev-parse','recovery/intent-radar-unpushed-f9350a8').decode().strip()==head
bundle=TEMP/'intent-radar-release-original-refs.bundle'
git('bundle','verify',str(bundle))
entries={}
for entry in git('ls-tree','-rz',head).split(b'\0'):
    if not entry:continue
    metadata,name=entry.split(b'\t',1);entries[name.decode()]=metadata
archives={'deploy/acquisition-validation.zip','deploy/brand-validation.zip','deploy/foundation-validation.zip'}
remove=sorted(name for name in entries if name in archives or any(part.startswith('.next') for part in Path(name).parts))
assert remove and all(Path(name).parts[0] in ('dashboard','deploy') for name in remove)
source={name:metadata for name,metadata in entries.items() if name not in remove}
print(json.dumps({'head':head,'base':base,'removing_generated_and_validation_paths':len(remove),'retaining_paths':len(source),'recovery_ref':'recovery/intent-radar-unpushed-f9350a8','bundle_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'mode':'apply' if args.apply else 'dry-run'},indent=2))
if args.apply:
    # Use a private index to preserve the user's source staging and worktree.
    with tempfile.TemporaryDirectory(prefix='intent-radar-23-git-repair-',dir=TEMP) as folder:
        env={**os.environ,'GIT_INDEX_FILE':str(Path(folder)/'index')}
        git('read-tree',head,env=env)
        names='\0'.join(remove).encode()+b'\0'
        git('update-index','--force-remove','-z','--stdin',env=env,input=names)
        tree=git('write-tree',env=env).decode().strip()
        new=git('commit-tree',tree,'-p',base,'-m','intent radar phase 2 and 3 (source-only history repair)',env=env).decode().strip()
        after={}
        for entry in git('ls-tree','-rz',new).split(b'\0'):
            if entry:
                metadata,name=entry.split(b'\t',1);after[name.decode()]=metadata
        assert after==source,'Every retained tracked path must keep its exact Git blob and mode.'
        git('update-ref','refs/heads/main',new,head)
        git('update-index','--force-remove','-z','--stdin',input=names)
        print(json.dumps({'reconstructed_commit':new,'source_blobs_and_modes_identical':True,'normal_fast_forward_parent':base,'working_files_deleted':False},indent=2))
