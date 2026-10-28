"""Send exact server secret values through CLI stdin, without argv/log exposure."""
import argparse
import shutil
import subprocess
from pathlib import Path
from dotenv import dotenv_values

root=Path(__file__).resolve().parents[1]


def configure(api_url):
    values=dotenv_values(root/'.env')
    values.update(APP_ENV='production',LEADENGINE_API_URL=api_url)
    executable=shutil.which('vercel')
    node=shutil.which('node')
    if not executable:raise RuntimeError('Vercel CLI unavailable')
    script=Path(executable).parent/'node_modules/vercel/dist/vc.js'
    command=[node,str(script)] if node and script.is_file() else [executable]
    for key in ['AUTH_SECRET','AUTH_GOOGLE_ID','AUTH_GOOGLE_SECRET','ALLOWED_USER_EMAILS','LEADENGINE_API_SIGNING_SECRET','LEADENGINE_API_URL','APP_ENV']:
        if not values.get(key):raise ValueError('Missing server environment key: '+key)
        subprocess.run([*command,'env','add',key,'production','--force','--sensitive'],input=values[key],text=True,cwd=root/'dashboard',check=True,timeout=60)
    print('Vercel server environment configured; values withheld.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--api-url');args=parser.parse_args()
    api_url=args.api_url or (root/'deploy/api-url.txt').read_text(encoding='utf-8-sig').strip()
    if not api_url.startswith('https://') or not api_url.endswith('.run.app'):raise ValueError('Verified HTTPS Cloud Run URL required')
    configure(api_url)
