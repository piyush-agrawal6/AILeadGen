"""Audited local-only cleanup. No database, provider or environment access."""
import argparse,hashlib,json,shutil,tempfile,zipfile,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TARGETS={'.pytest_cache':'reproducible test cache','dashboard/test-results':'generated browser run state','dashboard/.next/cache':'reproducible compiler cache'}
def run(apply=False):
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');rows=[];files=[]
 for name,purpose in TARGETS.items():
  root=ROOT/name
  if not root.exists():continue
  if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):raise ValueError('Generated tree contains a symlink; preserve for manual review.')
  paths=[p for p in root.rglob('*') if p.is_file()]
  if any(p.name.startswith('.env') for p in paths):raise ValueError('Environment file encountered; cleanup stopped.')
  rows.append({'path':name,'purpose':purpose,'files':len(paths),'bytes':sum(p.stat().st_size for p in paths)})
  files.extend(paths if name!='dashboard/.next/cache' else [])
 report={'created_at':stamp,'local_only':True,'targets':rows,'applied':False,'production_data_changed':False}
 if apply:
  backup=ROOT/'data/backups'/('heysow-generated-'+stamp+'.zip');backup.parent.mkdir(exist_ok=True)
  manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
  with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
   for p in files:z.write(p,p.relative_to(ROOT))
   z.writestr('manifest.json',json.dumps(manifest))
  backup.chmod(0o600)
  with tempfile.TemporaryDirectory(prefix='heysow-restore-') as scratch,zipfile.ZipFile(backup) as z:
   assert z.testzip() is None;z.extractall(scratch)
   for name,digest in manifest.items():assert hashlib.sha256((Path(scratch)/name).read_bytes()).hexdigest()==digest
  for r in rows:shutil.rmtree(ROOT/r['path'])
  report.update(applied=True,backup=str(backup.relative_to(ROOT)),restore_verified=True,compiler_cache='Regenerable compiler cache removed; no operational data or source files included.')
 path=ROOT/'docs'/('heysow-generated-cleanup-applied.json' if apply else 'heysow-generated-cleanup-dry-run.json');path.write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');run(p.parse_args().apply)
