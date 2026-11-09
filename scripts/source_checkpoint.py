"""Verified local source checkpoint. Never connects to a database or provider."""
import argparse
import hashlib
import json
import os
import re
import zipfile
from datetime import datetime,timezone
from pathlib import Path


def checkpoint(label):
    if not re.fullmatch(r'[a-z0-9-]{1,70}',label):raise ValueError('Use a short lowercase checkpoint label.')
    root=Path(__file__).resolve().parents[1]
    folder=root/'data/backups'/(label+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(parents=True,exist_ok=False,mode=0o700)
    archive=folder/'source.zip'
    blocked={'node_modules','.git','.venv','__pycache__','.pytest_cache','test-results','playwright-report','.next','.next-preview-test','.next-auth-test'}
    secret_suffixes={'.pem','.key','.p12','.pfx','.db','.sqlite','.pyc','.log'}
    selected=[]
    for directory in ('app','dashboard','scripts','tests','docs','config'):
        base=root/directory
        if not base.exists():continue
        for parent,children,files in os.walk(base,followlinks=False):
            children[:]=[name for name in children if name not in blocked and not name.startswith('.next') and not (Path(parent)/name).is_symlink()]
            for name in files:
                item=Path(parent)/name
                if name.startswith('.env') or item.suffix in secret_suffixes or item.is_symlink():continue
                selected.append(item)
    for pattern in ('*.toml','*.lock','*.py','package.json','package-lock.json','requirements*.txt','.gitignore','README.md','AGENTS.md','Dockerfile*','*.yaml','*.yml'):
        selected.extend(item for item in root.glob(pattern) if item.is_file() and not item.is_symlink())
    manifest={}
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
        archive.chmod(0o600)
        for item in sorted(set(selected)):
            name=item.relative_to(root).as_posix();body=item.read_bytes()
            output.writestr(name,body);manifest[name]=hashlib.sha256(body).hexdigest()
        output.writestr('CHECKPOINT_MANIFEST.json',json.dumps(manifest,indent=2))
    # Read every archived file back before claiming a verified checkpoint.
    with zipfile.ZipFile(archive) as saved:
        assert saved.testzip() is None
        for name,digest in manifest.items():assert hashlib.sha256(saved.read(name)).hexdigest()==digest
    record={'created_at':datetime.now(timezone.utc).isoformat(),'files':len(manifest),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_readback_verified':True,'includes_env':False,'includes_database':False,'production_changed':False}
    report=folder/'manifest.json';report.write_text(json.dumps(record,indent=2));report.chmod(0o600)
    print(json.dumps({'checkpoint':str(folder),'files':len(manifest),'verified':True}))
    return folder


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');checkpoint(parser.parse_args().label)
