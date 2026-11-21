"""Inventory a Git snapshot; output metadata only. Never open working .env files.

Protected projects supply read-only reference signals and have no inventory rows.
Lexical references are leads for manual review, not authority to delete a file.
"""
import argparse
from collections import defaultdict
import gzip
import io
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def protected(path):
    root = path.split('/')[0]
    return (root in {'dashboard', 'intent-radar-preview', 'planebyte-intent-radar-next'}
            or root.startswith(('planebyte-website', 'admin-panel'))
            or path.startswith('deploy/marketing/'))


def inventory(rev, target):
    rev = git('rev-parse', '--verify', rev+'^{commit}').decode().strip()
    tree = {}
    for entry in git('ls-tree', '-rlz', rev).split(b'\0'):
        if entry:
            head, path = entry.split(b'\t', 1)
            mode, kind, oid, size = head.split()
            if kind == b'blob':
                tree[path.decode()] = (oid.decode(), int(size))
    changes = git('diff', '--name-status', '--no-renames', '-z', rev, target).decode().split('\0')
    deleted = {f for action, f in zip(changes[::2], changes[1::2]) if action == 'D'}
    last = {}
    for line in git('log', '--format=#%H', '--name-only', rev).decode().splitlines():
        if re.fullmatch(r'#[0-9a-f]{40}', line):
            commit = line[1:]
        elif line in tree:
            last.setdefault(line, commit)
    refs = defaultdict(lambda: defaultdict(set))
    env = defaultdict(set)
    names = defaultdict(set)
    for path in tree:
        if protected(path):
            continue
        names[Path(path).name].add(path)
        if path.endswith('.py'):
            names[path[:-3].replace('/', '.')].add(path)
    raw = subprocess.check_output(['git','cat-file','--batch'], cwd=ROOT,
                                  input=''.join(oid+'\n' for oid,_ in tree.values()).encode())
    stream = io.BytesIO(raw)
    for path in tree:
        _, _, size = stream.readline().split(); data = stream.read(int(size)); stream.read(1)
        if b'\0' in data or Path(path).name.startswith('.env') or len(data)>2_000_000:
            continue
        text = data.decode(errors='replace')
        group = ('protected-client' if protected(path) else 'ci' if path.startswith('.github/')
                 else 'deployment' if path.startswith('deploy/') else 'test' if path.startswith('tests/')
                 else 'docs' if path.startswith('docs/') else 'source')
        origin = '(protected client)' if protected(path) else path
        for token in set(re.findall(r'[A-Za-z_][\w.-]*',text)):
            for hit in names.get(token, ()):
                if path != hit: refs[hit][group].add(origin)
        for mod in re.findall(r'^\s*(?:from|import)\s+([\w.]+)',text,re.M):
            for hit in names.get(mod, ()):
                if path!=hit:refs[hit]['import'].add(origin)
        if not protected(path):
            env[path].update(re.findall(r'''(?:getenv\(|environ(?:\.get\(|\[)|alias=)["']([A-Z][A-Z_0-9]+)["']''',text))
    for path,(oid,size) in sorted(tree.items()):
        if protected(path):continue
        if path in deleted: label, action='DELETE','See reviewed deletion groups in the cleanup report'
        elif path.startswith('app/database/'):label, action='RETAIN FOR HISTORY','Preserve database lineage and shared infrastructure'
        elif path.startswith('tests/') and (Path(path).name.startswith('test_') or Path(path).name=='conftest.py'):
            label,action='KEEP','Configured pytest testpaths and full PostgreSQL regression on hosted CI'
        elif path in {'requirements.lock','pyproject.toml','requirements.txt','.nvmrc','.gitignore','.dockerignore','.gcloudignore','.vercelignore','AGENTS.md','README.md','.env.example','release-policy.json'}:
            label,action='KEEP','Maintained build, packaging, release policy, environment template or operator entry point'
        elif refs[path]['ci'] and path.startswith(('scripts/','deploy/')):
            label,action='KEEP','Referenced by CI; release verification requires this interface'
        elif path.startswith(('app/billing/','app/api/','app/platform/')) or path=='app/worker.py':label,action='REFACTOR','Review shared consumers before changing interfaces'
        elif path.startswith(('app/intent_radar/','app/accounts/','app/growth_intelligence/','.github/')):label,action='KEEP','Product or release surface'
        else:label,action='UNRESOLVED','Retain pending operational review'
        yield dict(path=path,type=Path(path).suffix or 'extensionless',bytes=size,tracked=True,
                   blob=oid,last_commit=last.get(path),references={k:sorted(v) for k,v in refs[path].items()},
                   environment_names=sorted(env[path]),classification=label,action=action)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('baseline');parser.add_argument('target');parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with args.output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:
        for row in inventory(args.baseline,args.target):z.write((json.dumps(row,sort_keys=True)+'\n').encode())
