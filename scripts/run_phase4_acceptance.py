import os,subprocess,sys
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1];env=os.environ.copy()
for file in (root/'.env',root/'dashboard/.env',root/'dashboard/.env.local'):env.update({k:v for k,v in dotenv_values(file).items() if v is not None})
env['CHECK_EMAIL']='planebyte@gmail.com'
raise SystemExit(subprocess.run(['node','scripts/phase4-acceptance.mjs',*sys.argv[1:]],cwd=root/'dashboard',env=env).returncode)
