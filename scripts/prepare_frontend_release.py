"""Package one committed, integrated frontend. Does not deploy or change settings."""
import argparse,io,json,subprocess,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def ancestor(base,head):
 if subprocess.run(['git','merge-base','--is-ancestor',base,head],cwd=ROOT,capture_output=True).returncode:raise RuntimeError('Release is missing source ancestry: '+base)
def prepare(destination,deployed_source):
 policy=json.loads((ROOT/'dashboard/release-policy.json').read_text());head=git('rev-parse','HEAD')
 if git('branch','--show-current')!=policy['branch']:raise RuntimeError('Deploy only from '+policy['branch'])
 if git('status','--porcelain','--untracked-files=all','--','dashboard','app/accounts/email_policy.json'):raise RuntimeError('Commit and verify frontend changes before packaging')
 for ref in [policy['ui_baseline'],policy['backend_baseline'],deployed_source,*policy['feature_refs']]:ancestor(ref,head)
 # A sibling agent's tracked frontend changes must be integrated, never ignored.
 for section in git('worktree','list','--porcelain').split('\n\n'):
  if not section:continue
  folder=section.splitlines()[0].removeprefix('worktree ')
  dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','dashboard','app/accounts/email_policy.json'],cwd=folder,text=True).strip()
  if dirty:raise RuntimeError('Unintegrated frontend changes in '+folder)
 destination=destination.resolve();destination.relative_to((ROOT/'data/artifacts/staging').resolve());destination.mkdir(mode=0o700,parents=True,exist_ok=False)
 archive=subprocess.check_output(['git','archive','--format=tar',head,'dashboard','app/accounts/email_policy.json'],cwd=ROOT)
 with tarfile.open(fileobj=io.BytesIO(archive)) as source:source.extractall(destination,filter='data')
 manifest={k:policy[k] for k in ('branch','ui_baseline','backend_baseline')}
 manifest.update(source_commit=head,frontend_tree=git('rev-parse',head+':dashboard'),previous_frontend_source=deployed_source,prepared_at=datetime.now(timezone.utc).isoformat())
 (destination/'dashboard/public/release.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);parser.add_argument('--deployed-source',required=True);args=parser.parse_args();print(json.dumps(prepare(args.destination,args.deployed_source)))
