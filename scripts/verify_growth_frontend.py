"""Isolated Growth UI build/browser verification with fixture-only credentials."""
import argparse,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=ROOT/'data/artifacts/runtime/node-v24.22.2-darwin-x64/bin'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('check',choices=['build','browser','billing-browser','units','types']);args=parser.parse_args()
    env={**os.environ,'PATH':str(NODE)+os.pathsep+os.environ['PATH']}
    env.update(APP_ENV='test',DATABASE_BACKEND='sqlite',DATABASE_URL='',UPSTASH_REDIS_REST_URL='',UPSTASH_REDIS_REST_TOKEN='',
      AUTH_SECRET='fixture-session-secret-only-for-local-tests-123456789',LEADENGINE_API_SIGNING_SECRET='fixture-signing-secret-only-for-local-tests-123456789',
      AUTH_GOOGLE_ID='synthetic-google-id',AUTH_GOOGLE_SECRET='synthetic-google-secret',ALLOWED_USER_EMAILS='founder@leadengine.example,cofounder@leadengine.example',
      AUTH_URL='http://127.0.0.1:13000',AUTH_DISABLED_LOCAL='false',LEADENGINE_API_URL='http://127.0.0.1:18787',HEYSOW_E2E_DIST_DIR='.next-growth-build',
      VERTEX_AI_ENABLED='false',GEMINI_API_ENABLED='false',GEMINI_API_KEY='',GMAIL_APP_PASSWORD='',EMAIL_SENDING_ENABLED='false',AUTO_EMAIL_ENABLED='false',AUTO_SCAN_ENABLED='false',
      INTENT_RADAR_GROWTH_ENABLED='true',INTENT_RADAR_STAGE='Beta',INTENT_RADAR_AI_ENABLED='false',HEYSOW_WORKSPACE_MANAGEMENT_ENABLED='true')
    command={'build':['../scripts/local_frontend.cjs','build','--webpack'],
      'browser':['node_modules/@playwright/test/cli.js','test','--config=playwright.growth.config.ts'],
      'billing-browser':['node_modules/@playwright/test/cli.js','test','--config=playwright.billing.config.ts'],
      'units':['node_modules/vitest/vitest.mjs','run','--maxWorkers=2'],
      'types':['node_modules/typescript/bin/tsc','--noEmit']}[args.check]
    raise SystemExit(subprocess.run([str(NODE/'node'),*command],cwd=ROOT/'dashboard',env=env,timeout=1200).returncode)
if __name__=='__main__':main()
