"""Create an immutable, read-back verified source recovery archive (no credentials)."""
import hashlib
import json
import subprocess
import zipfile
import argparse
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',default=str(base/'intent-radar-23-20261110T164430742471Z'/'manifest.json'))
parser.add_argument('--output',type=Path,help='New immutable checkpoint directory inside the approved temporary root')
args=parser.parse_args()
output = args.output.resolve() if args.output else base / ('intent-radar-23-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
assert output.parent==base.resolve() and output.name.startswith('intent-radar-23-') and not output.exists()
output.mkdir(mode=0o700)
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
paths = sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''})
hashes = {}
archive = output / 'source.zip'
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for name in paths:
        p = Path(name)
        if any(x.startswith(('.env', '.next', '__pycache__')) for x in p.parts): continue
        if p.parts[0] not in {'app', 'dashboard', 'docs', 'scripts', 'tests', 'config'} and p.parent != Path('.'): continue
        if p.suffix in {'.db', '.sqlite', '.pyc', '.pem', '.key', '.zip', '.pack', '.gz'}: continue
        if any(x in {'node_modules', 'artifacts', 'test-results', 'playwright-report'} for x in p.parts): continue
        if not (root / p).is_file(): continue
        value = (root / p).read_bytes()
        hashes[name] = hashlib.sha256(value).hexdigest()
        z.writestr(name, value)
    z.writestr('CHECKPOINT/status.txt', git('status', '--short', '--branch'))
    # Source-only diff: excludes generated output and environment files.
    z.writestr('CHECKPOINT/source.diff', git('diff', '--binary', '--', *hashes))
archive.chmod(0o600)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name, digest in hashes.items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest
manifest = output / 'manifest.json'
evidence_hashes={}
evidence_archive=output/'verification.zip'
evidence_root=root/'data/artifacts/verification'
with zipfile.ZipFile(evidence_archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    evidence_paths=[p for p in evidence_root.glob('intent-radar23-*') if p.is_file() and p.suffix in {'.log','.xml','.json'}]
    evidence_paths.extend(evidence_root.glob('intent-radar23-*/**/*.png'))
    evidence_paths.extend(evidence_root.glob('intent-radar23-*/**/trace.zip'))
    for p in sorted(evidence_paths):
        name=str(p.relative_to(root));value=p.read_bytes()
        evidence_hashes[name]=hashlib.sha256(value).hexdigest();z.writestr(name,value)
evidence_archive.chmod(0o600)
with zipfile.ZipFile(evidence_archive) as z:
    assert z.testzip() is None
    for name,digest in evidence_hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
baseline=Path(args.baseline).resolve()
original=json.loads(baseline.read_text())['source_sha256'] if baseline.is_relative_to(base.resolve()) and baseline.is_file() else {}
changed=sorted(name for name,digest in hashes.items() if original.get(name)!=digest)
manifest.write_text(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), 'source_sha256': hashes,
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'readback_verified': True,
    'baseline':str(baseline),'changed_since_baseline':changed,
    'verification_sha256':evidence_hashes,'verification_archive_sha256':hashlib.sha256(evidence_archive.read_bytes()).hexdigest(),'verification_readback_verified':True}, indent=2))
manifest.chmod(0o600)
latest=base/'intent-radar-23-LATEST.json'
latest.write_text(json.dumps({'checkpoint':str(output),'manifest':str(manifest),'readback_verified':True},indent=2))
latest.chmod(0o600)
print(json.dumps({'checkpoint': str(output), 'files': len(hashes), 'readback_verified': True,'verification_files':len(evidence_hashes),'verification_readback_verified':True,'changed_since_baseline':changed}))
