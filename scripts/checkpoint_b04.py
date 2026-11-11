"""Readback-verified B04 source/evidence checkpoint; no Git or database mutation."""
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

root = Path(__file__).resolve().parents[1]
evidence = root / 'data/artifacts/verification/phase6/b04-completion-20261110'
archive = evidence / 'source-checkpoint.zip'
manifest = evidence / 'results.json'
assert evidence.is_dir() and not archive.exists() and not manifest.exists()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

def junit(name):
    cases = ElementTree.parse(evidence / name).findall('.//testcase')
    assert all(c.find('failure') is None and c.find('error') is None for c in cases)
    skipped = [c for c in cases if c.find('skipped') is not None]
    return {'passed':len(cases)-len(skipped), 'skipped':len(skipped), 'failed':0,
            'skip_reasons':sorted({c.find('skipped').get('message', '') for c in skipped})}

browser = {}
for name, file in [('gmail','browser-results.json'),('lead_engine','lead-engine-browser-results.json'),('intent_radar','radar-browser-results.json')]:
    stats = json.loads((evidence / file).read_text())['stats']
    assert stats['unexpected'] == stats['flaky'] == 0
    browser[name] = stats
frontend = (evidence / 'frontend-final.log').read_text()
assert 'failed' not in frontend.lower()
assert 'Compiled successfully' in (evidence / 'build.log').read_text()
assert 'error TS' not in (evidence / 'typecheck-final.log').read_text()
paths = sorted(set(git('ls-files','-z','--modified','--others','--exclude-standard').decode().split('\0'))-{''})
sources = [p for p in paths if not any(part.startswith(('.env','.next')) for part in Path(p).parts)]
hashes = {}
deleted = []
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sources:
        if not (root / p).is_file():
            deleted.append(p)
            continue
        value = (root / p).read_bytes()
        hashes[p] = hashlib.sha256(value).hexdigest()
        z.writestr(p,value)
    z.writestr('CHECKPOINT/source-diff.patch',git('diff','--binary','--','.',':(exclude)dashboard/.next*'))
    z.writestr('CHECKPOINT/git-status.txt',git('status','--short'))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p, digest in hashes.items():assert hashlib.sha256(z.read(p)).hexdigest() == digest
result = {'milestone':'B04', 'status':'IMPLEMENTED_AND_LOCALLY_VERIFIED_STOP',
          'created_at':datetime.now(timezone.utc).isoformat(), 'head':git('rev-parse','HEAD').decode().strip(),
          'backend_full':junit('backend-full.xml'), 'backend_focused_final':junit('backend-focused-verified.xml'),
          'full_run_note':'Final focused run includes an additional rejected-refresh case added after the full suite.',
          'frontend_passed':int(re.search(r'Tests\s+(\d+) passed',frontend).group(1)),
          'browser':browser, 'typecheck':'PASS','build':'PASS','postgresql':'BLOCKED',
          'source_archive':str(archive.relative_to(root)), 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
          'archive_readback_verified':True, 'source_sha256':hashes,'deleted_source_paths':deleted,
          'exclusions':'Secrets/environment files and generated Next directories; no files reset/untracked.',
          'external_acceptance':'Real OAuth/Gmail/live-send and PostgreSQL acceptance require separate owner authorization; not performed.'}
with manifest.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({'checkpoint':str(manifest.relative_to(root)),'source_files':len(hashes),
                  'archive_readback_verified':True,'backend_full':result['backend_full'],
                  'backend_focused_final':result['backend_focused_final'],
                  'frontend_passed':result['frontend_passed'],
                  'browser_passed':{k:v['expected'] for k,v in browser.items()}},indent=2))
