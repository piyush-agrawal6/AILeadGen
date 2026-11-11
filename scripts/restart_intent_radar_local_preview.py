"""Back up/readback-check the existing local SQLite preview, then restart its API.

Explicit local repair only. Does not activate providers, change environment files,
restart the frontend, or modify deployment infrastructure.
"""
import argparse
import json
import os
import signal
import sqlite3
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.replace('-','').isalnum()
BASE=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
database=ROOT/'data/e2e/local-preview/workspace.db'
assert database.is_file() and BASE.is_dir()
backup=BASE/f'intent-radar-23-product-preview-backup-{args.label}.db'
assert not backup.exists()
source=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)
target=sqlite3.connect(backup)
source.backup(target)
assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
tables=['businesses','contact_people','contacted_recipients','contacted_recipient_sends','email_messages','intent_monitors','intent_signals','organization_memberships']
counts={}
for table in tables:
    original=source.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
    assert target.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==original
    counts[table]=original
source.close();target.close();backup.chmod(0o600)
rows=subprocess.check_output(['ps','-axo','pid,command'],text=True).splitlines()
matches=[int(row.strip().split(' ',1)[0]) for row in rows if ' -m uvicorn app.api.server:app --host 127.0.0.1 --port 18790' in row and str(ROOT/'.venv/bin/python') in row]
assert len(matches)==1, 'Only the known existing local-preview process may be restarted.'
os.kill(matches[0],signal.SIGTERM)
for _ in range(100):
    try:os.kill(matches[0],0)
    except ProcessLookupError:break
    time.sleep(.1)
else:raise RuntimeError('Existing preview did not exit; no replacement launched.')
log=BASE/f'intent-radar-23-product-preview-server-{args.label}.log'
with log.open('x') as output:
    process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'scripts/local_preview.py','backend'],cwd=ROOT,
        stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
import httpx
for _ in range(100):
    if process.poll() is not None:raise RuntimeError('Replacement preview exited; inspect local log without printing secrets.')
    try:
        if httpx.get('http://127.0.0.1:18790/api/health',timeout=1,trust_env=False).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.1)
else:raise RuntimeError('Replacement preview did not become healthy within bounded startup wait.')
result={'old_pid':matches[0],'new_pid':process.pid,'backup':str(backup),'backup_integrity':'ok','preserved_counts':counts,'log':str(log)}
(BASE/f'intent-radar-23-product-preview-restart-{args.label}.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
