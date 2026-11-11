"""Isolated current-checkout acceptance runner with additive logs and Node 24."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/node-v24.22.2-darwin-x64/bin')
EVIDENCE = ROOT/'data/artifacts/verification'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('check', choices=['backend','postgres','units','types','build','browser','live-sources','live-ai','runtime'])
parser.add_argument('--suite', default='phase23')
parser.add_argument('--label', default='final')
args = parser.parse_args()
assert EVIDENCE.is_dir()
assert args.label.replace('-', '').isalnum() and args.suite.replace('-', '').isalnum()
env = os.environ.copy()
env.update(APP_ENV='test', DATABASE_BACKEND='sqlite', DATABASE_URL='', UPSTASH_REDIS_REST_URL='', UPSTASH_REDIS_REST_TOKEN='')
python = str(ROOT/'.venv/bin/python')
cwd = ROOT
name = args.check + ('-'+args.suite if args.check=='browser' else '')+'-'+args.label
log = EVIDENCE/f'intent-radar23-product-{name}.log'
assert not log.exists(), 'Preserve previous evidence; choose a new label.'
if args.check in ('backend','postgres'):
    targets = ['tests'] if args.check=='backend' else ['tests/integration/test_postgres.py','tests/integration/test_intent_radar_postgres.py']
    command = [python,'-m','pytest',*targets,'-q','--junitxml='+str(EVIDENCE/f'intent-radar23-product-{name}.xml')]
    if args.check=='postgres':
        env.update(RUN_POSTGRES_TESTS='1', DATABASE_URL='postgresql://radar_test@127.0.0.1:15443/intent_radar23_acceptance_utf8')
        env['PATH']=str(ROOT/'data/artifacts/postgres-local/install/bin')+os.pathsep+env['PATH']
elif args.check in ('units','types','build','browser'):
    assert (NODE/'node').is_file()
    env['PATH']=str(NODE)+os.pathsep+env['PATH']
    cwd = ROOT/'dashboard'
    if args.check=='units':
        command=[str(NODE/'node'),'node_modules/vitest/vitest.mjs','run','--maxWorkers=2']
    elif args.check=='types':
        command=[str(NODE/'node'),'node_modules/typescript/bin/tsc','--noEmit']
    elif args.check=='build':
        env.update(AUTH_SECRET='fixture-session-secret-only-for-local-tests-123456789',
            LEADENGINE_API_SIGNING_SECRET='fixture-signing-secret-only-for-local-tests-123456789',
            AUTH_GOOGLE_ID='synthetic-audit-google-id',AUTH_GOOGLE_SECRET='synthetic-audit-google-secret',
            ALLOWED_USER_EMAILS='founder@leadengine.example,cofounder@leadengine.example',
            LEADENGINE_API_URL='http://127.0.0.1:18787',AUTH_URL='http://127.0.0.1:13000',
            AUTH_DISABLED_LOCAL='false',HEYSOW_E2E_DIST_DIR='.next-intent-radar23-product-build',
            INTENT_RADAR_STAGE='Beta',INTENT_RADAR_AI_ENABLED='false',VERTEX_AI_ENABLED='false',GEMINI_API_ENABLED='false')
        command=[str(NODE/'node'),'../scripts/local_frontend.cjs','build','--webpack']
    else:
        env.update(RADAR_PRODUCT_SUITE=args.suite,RADAR_PRODUCT_LABEL=args.label,RADAR23_REGRESSION='radar' if args.suite=='radar' else 'lead-engine',RADAR23_EVIDENCE_ROOT=str(EVIDENCE/f'intent-radar23-product-{args.suite}-{args.label}'))
        if args.suite.startswith('platform-'):env['RADAR23_PLATFORM_SUITE']=args.suite.split('-',1)[1]
        command=[str(NODE/'node'),'node_modules/@playwright/test/cli.js','test','--config=playwright.intent-radar-product.config.ts']
elif args.check=='live-sources':
    command=[python,'scripts/verify_intent_radar_23_live.py','--database',
        '/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-product-live.db','--public-meta-feed','--hn-jobs']
elif args.check=='live-ai':
    command=[python,'scripts/evaluate_intent_radar_ai.py','--live']
else:
    command=[python,'scripts/inspect_intent_radar_product_runtime.py']
start=time.monotonic()
with log.open('x') as output:
    result=subprocess.run(command,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=1200)
record={'check':args.check,'suite':args.suite,'label':args.label,'returncode':result.returncode,
    'duration_seconds':round(time.monotonic()-start,2),'command':command,'log':str(log.relative_to(ROOT)),
    'node':'24.22.2' if args.check in ('units','types','build','browser') else None}
(EVIDENCE/f'intent-radar23-product-{name}.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
print(log.read_text())
raise SystemExit(result.returncode)
