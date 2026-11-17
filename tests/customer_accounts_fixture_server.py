"""Isolated signed HTTP/auth/worker fixture. Never mounted by production.

Only company, AI, source and email transports are synthetic. Real password KDF,
OTP verification, Auth.js JWT, HMAC broker, DB quota and workspace checks run.
"""
import re,uuid
from fastapi import Request,HTTPException
from pydantic import SecretStr
from tests.onboarding_fixture_server import app,settings,path
from app.accounts import policy
from app.notifications import transactional as mail
from app.database.connection import db_session
from app.api.organization import create_organization
settings.app_env='development'
settings.auth_disabled_local=False
settings.heysow_accounts_enabled=True
settings.heysow_access_periods_enabled=True
settings.heysow_customer_access_enabled=True
settings.heysow_public_registration_enabled=True
settings.heysow_invited_registration_enabled=True
settings.heysow_terms_version='synthetic-browser-terms-v1'
settings.heysow_google_admission_client_id='synthetic-account-browser-client'
settings.transactional_mail_enabled=True
settings.resend_api_key=SecretStr('fixture-only-no-provider-network')
settings.resend_from_email='PlaneByte <accounts@planebyte.com>'
settings.allowed_user_emails='founder@example.com'
with db_session() as c:
    create_organization(c,'founder@example.com','Isolated mailbox operator')
policy.mailbox_domain_available=lambda _:True
captured=[]
def send(payload,key):
    assert settings.resend_api_key.get_secret_value()=='fixture-only-no-provider-network'
    captured.append({'key':key,'payload':payload})
    return str(uuid.uuid4())
mail.send_provider=send
@app.get('/api/organization/_test/mailbox')
def mailbox(request:Request,email:str):
    if request.state.user_email!='founder@example.com' or not getattr(request.state,'internal_verified',False):raise HTTPException(403)
    rows=[m['payload'] for m in captured if m['payload']['to']==[email]]
    return {'messages':rows}
