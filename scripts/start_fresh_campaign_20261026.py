import os,subprocess
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1];env=os.environ.copy()
for path in (root/'.env',root/'dashboard/.env',root/'dashboard/.env.local'):env.update({k:v for k,v in dotenv_values(path).items() if v is not None})
env['CHECK_EMAIL']='planebyte@gmail.com'
raise SystemExit(subprocess.run(['node','scripts/fresh-campaign-20261026.mjs'],cwd=root/'dashboard',env=env).returncode)
