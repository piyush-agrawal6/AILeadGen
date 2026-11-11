"""Run an authenticated local preview with an isolated database.

Usage: .venv/bin/python scripts/local_preview.py backend|frontend [--icp-ai|--all-features]
Existing root .env remains untouched; no secret values are printed.
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import dotenv_values

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode',choices=('frontend','backend'))
parser.add_argument('--icp-ai',action='store_true',help='Explicitly allow bounded ICP requests through existing Vertex ADC; no discovery or sending.')
parser.add_argument('--all-features',action='store_true',help='Enable implemented local SaaS features/providers; preserve authentication and the no-real-email restriction.')
parser.add_argument('--mail-test-to',help='Backend-only owner-approved mailbox; all SMTP delivery is redirected here.')
args=parser.parse_args()
if args.icp_ai and args.mode!='backend':parser.error('--icp-ai applies only to the backend.')
if args.mail_test_to:
    if args.mode!='backend' or not args.all_features:parser.error('--mail-test-to requires backend --all-features.')
    import re
    if not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',args.mail_test_to) or len(args.mail_test_to)>254:
        parser.error('Use one valid controlled mailbox address.')
    args.mail_test_to=args.mail_test_to.lower()
values=dotenv_values(root/'.env')
environment=os.environ.copy()
for name in ('AUTH_GOOGLE_ID','AUTH_GOOGLE_SECRET','AUTH_SECRET','ALLOWED_USER_EMAILS','LEADENGINE_API_SIGNING_SECRET'):
    if values.get(name):environment[name]=values[name]
environment.update({
    'APP_ENV':'development','DATABASE_BACKEND':'sqlite','DATABASE_URL':'',
    'HEYSOW_LOCAL_PREVIEW':'true',
    'SCAN_EXECUTOR':'local',
    'STORAGE_BACKEND':'local',
    'DATABASE_PATH':str(root/'data/e2e/local-preview/workspace.db'),
    'ARTIFACT_LOCAL_ROOT':str(root/'data/e2e/local-preview/artifacts'),
    'LEADENGINE_API_URL':'http://127.0.0.1:18790','AUTH_URL':'',
    'AUTH_DISABLED_LOCAL':'false','HEYSOW_WORKSPACE_MANAGEMENT_ENABLED':'true',
    'HEYSOW_INTERNAL_EXPERIMENTS_ENABLED':'false',
    # A local Beta stage does not grant access: organization_products and
    # completed onboarding still gate every page, API and worker.
    'INTENT_RADAR_STAGE':'Beta',
    'INTENT_RADAR_AI_ENABLED':'false',
    'AUTO_SCAN_ENABLED':'false','AUTO_EMAIL_ENABLED':'false',
    'EMAIL_SENDING_ENABLED':'false','EMAIL_SYNC_ENABLED':'false',
    'EMAIL_TRACKING_BASE_URL':'http://localhost:3000/t',
    'ENABLE_AI_ACQUISITION':'false','ENABLE_FIRECRAWL_ACQUISITION':'false',
    'ENABLE_LEAD_IMPORT':'false','ENABLE_GOOGLE_SHEETS_IMPORT':'false',
    'VERTEX_AI_ENABLED':'false','GEMINI_API_ENABLED':'false',
    'HEYSOW_ICP_AI_ENABLED':'false',
    'GEMINI_API_KEY':'','FIRECRAWL_API_KEY':'','GMAIL_APP_PASSWORD':'',
    'GMAIL_ENABLED':'false','MAIL_PASSWORD':'',
    'UPSTASH_REDIS_REST_URL':'','UPSTASH_REDIS_REST_TOKEN':'',
})
if args.icp_ai or args.all_features:
    for name in ('VERTEX_AI_PROJECT_ID','VERTEX_AI_LOCATION','VERTEX_AI_MODEL','HEYSOW_ICP_AI_DAILY_LIMIT','HEYSOW_ICP_AI_GLOBAL_DAILY_LIMIT'):
        if values.get(name):environment[name]=values[name]
    environment.update({'HEYSOW_ICP_AI_ENABLED':'true','VERTEX_AI_ENABLED':'true',
        'AI_PROVIDER':'vertex','AI_PRIMARY_PROVIDER':'vertex','AI_FALLBACK_ENABLED':'false'})
if args.all_features:
    for name in ('HEYSOW_COMPANY_DISCOVERY_ENABLED','HEYSOW_COMPANY_AI_ENABLED','HEYSOW_LEAD_ASSISTANT_ENABLED',
                 'HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED','HEYSOW_DEVELOPER_API_ENABLED','HEYSOW_MCP_ENABLED','HEYSOW_WEBHOOKS_ENABLED',
                 'ENABLE_AI_ACQUISITION','ENABLE_FIRECRAWL_ACQUISITION','ENABLE_LEAD_IMPORT','ENABLE_GOOGLE_SHEETS_IMPORT',
                 'AUTO_SCAN_ENABLED'):
        environment[name]='true'
    if args.mode=='backend':
        for name in ('FIRECRAWL_API_KEY','HEYSOW_INTEGRATION_ENCRYPTION_KEY','UPSTASH_REDIS_REST_URL','UPSTASH_REDIS_REST_TOKEN'):
            if values.get(name):environment[name]=values[name]
        environment['GOOGLE_SHEETS_REDIRECT_URI']='http://localhost:3000/acquisition/sheets/callback'
if args.mail_test_to:
    for name in ('GMAIL_USERNAME','GMAIL_APP_PASSWORD','GMAIL_SMTP_HOST','GMAIL_SMTP_PORT','GMAIL_SMTP_SECURE',
                 'GMAIL_IMAP_HOST','GMAIL_IMAP_PORT','GMAIL_IMAP_SECURE','MAIL_FROM_NAME','MAIL_FROM_ADDRESS',
                 'MAX_EMAILS_PER_HOUR','MAX_EMAILS_PER_DAY','DEFAULT_FOLLOWUP_DAYS'):
        if values.get(name):environment[name]=values[name]
    environment.update({'EMAIL_PROVIDER':'gmail','GMAIL_ENABLED':'true','EMAIL_SENDING_ENABLED':'true',
        'AUTO_EMAIL_ENABLED':'true','EMAIL_SYNC_ENABLED':'true','EMAIL_SEND_MODE':'test',
        'EMAIL_TEST_RECIPIENT':args.mail_test_to,'EMAIL_LIVE_APPROVED':'false'})
if args.mode=='frontend':
    os.chdir(root/'dashboard')
    os.execvpe('node',['node',str(root/'scripts/local_frontend.cjs'),'dev','--webpack','--hostname','127.0.0.1','--port','3000'],environment)
else:
    os.chdir(root)
    os.execve(sys.executable,[sys.executable,'-m','uvicorn','app.api.server:app','--host','127.0.0.1','--port','18790'],environment)
