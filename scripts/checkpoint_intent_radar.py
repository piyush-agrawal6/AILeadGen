"""Preserve dirty source and verified results without touching Git or databases."""
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

root = Path(__file__).resolve().parents[1]
output = root / 'data/artifacts/verification/intent-radar'
assert output.is_dir()
archive = output / 'source-checkpoint.zip'
manifest = output / 'source-checkpoint.json'
assert not archive.exists() and not manifest.exists(), 'Never overwrite a checkpoint.'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

cases = ElementTree.parse(output / 'backend-final.xml').findall('.//testcase')
failed = sum(c.find('failure') is not None for c in cases)
errors = sum(c.find('error') is not None for c in cases)
skips = [c for c in cases if c.find('skipped') is not None]
assert not failed and not errors
backend = {'passed': len(cases)-len(skips), 'failed': failed, 'errors': errors, 'skipped': len(skips),
           'intent_radar_passed': sum('test_intent_radar' in c.get('classname', '') for c in cases),
           'skip_reasons': sorted({c.find('skipped').get('message', '') for c in skips})}
browsers = {}
for name, file in [('intent_radar', 'browser-results.json'), ('lead_engine', 'lead-engine-browser-results.json')]:
    stats = json.loads((output / file).read_text())['stats']
    assert stats['unexpected'] == 0 and stats['flaky'] == 0
    browsers[name] = stats
frontend = (output / 'frontend-corrected-final.log').read_text()
assert 'failed' not in frontend.lower()
frontend_passes = int(re.search(r'Tests\s+(\d+) passed', frontend).group(1))
assert 'Compiled successfully' in (output / 'build-final.log').read_text()

paths = sorted(set(git('ls-files', '-z', '--modified', '--others', '--exclude-standard').decode().split('\0')) - {''})
assert all(not any(part.startswith('.env') for part in Path(p).parts) for p in paths)
hashes = {}
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for path in paths:
        value = (root / path).read_bytes()
        hashes[path] = hashlib.sha256(value).hexdigest()
        z.writestr(path, value)
    z.writestr('CHECKPOINT/git-diff.patch', git('diff', '--binary'))
    z.writestr('CHECKPOINT/git-status.txt', git('status', '--short'))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for path, digest in hashes.items():
        assert hashlib.sha256(z.read(path)).hexdigest() == digest
result = {'created_at': datetime.now(timezone.utc).isoformat(), 'head': git('rev-parse', 'HEAD').decode().strip(),
          'archive': str(archive.relative_to(root)), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'archive_readback_verified': True, 'source_sha256': hashes, 'backend': backend,
          'browsers': browsers, 'frontend_passed': frontend_passes, 'typecheck': 'PASS', 'build': 'PASS',
          'postgresql': 'BLOCKED: no local server/runtime; not verified',
          'lead_engine_resume': 'B04 frontend and broader worker/API closure; see docs/LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md'}
with manifest.open('x') as f:
    json.dump(result, f, indent=2)
print(json.dumps({'checkpoint': str(manifest.relative_to(root)), 'source_files': len(hashes),
                  'archive_readback_verified': True, 'backend': backend, 'frontend_passed': frontend_passes,
                  'browser_passes': {name: stats['expected'] for name, stats in browsers.items()}}, indent=2))
