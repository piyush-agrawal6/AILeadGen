"""Publish/check the authoritative nonsecret catalog in Planebyte-Landing.

No provider credentials, backend logic, legal policy, or deployment configuration
is copied. Run --check in release verification for both repositories.
"""
import argparse,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'app/billing/commercial_catalog.json'

def main():
    p=argparse.ArgumentParser();p.add_argument('--marketing-root',type=Path,required=True);p.add_argument('--check',action='store_true');args=p.parse_args()
    root=args.marketing_root.resolve()
    if not (root/'.git').exists() or not (root/'src/components/family-pricing.tsx').is_file():raise SystemExit('Expected existing marketing repository, not a new site.')
    destination=root/'src/config/intent-radar-catalog.json';raw=SOURCE.read_bytes()
    if args.check:
        if not destination.is_file() or destination.read_bytes()!=raw:raise SystemExit('Commercial catalog drift: synchronize before deploying either application.')
        component=(root/'src/components/family-pricing.tsx').read_text()
        if '@/config/intent-radar-catalog.json' not in component:raise SystemExit('Public pricing must render the synchronized catalog.')
    else:destination.write_bytes(raw)
    data=json.loads(raw)
    print(json.dumps({'catalog_version':data['version'],'catalog_sha256':hashlib.sha256(raw).hexdigest(),'matching':True,'checkout_enabled':False}))
if __name__=='__main__':main()
