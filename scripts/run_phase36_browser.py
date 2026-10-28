"""Run bounded production checks without placing session secrets in argv/output."""
import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1]
env=os.environ.copy()
for path in (root/'.env',root/'dashboard/.env',root/'dashboard/.env.local'):
    env.update({k:v for k,v in dotenv_values(path).items() if v is not None})
env['CHECK_EMAIL']='planebyte@gmail.com'
raise SystemExit(subprocess.run(['node','scripts/phase36-production.mjs',*sys.argv[1:]],cwd=root/'dashboard',env=env).returncode)
