"""Server-only mailbox settings. Never serialize this object to an API response."""
from pathlib import Path
from zoneinfo import ZoneInfo
from pydantic import Field,SecretStr,model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class MailSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / '.env',env_file_encoding='utf-8',extra='ignore',hide_input_in_errors=True)
    provider:str=Field('gmail',alias='EMAIL_PROVIDER')
    mode:str=Field('test',alias='EMAIL_SEND_MODE')
    test_recipient:str=Field('',alias='EMAIL_TEST_RECIPIENT',repr=False)
    from_name:str=Field('PlaneByte',alias='MAIL_FROM_NAME')
    from_address:str=Field('planebyte@gmail.com',alias='MAIL_FROM_ADDRESS')
    username:str=Field('rajendra@planebyte.com',alias='MAIL_USERNAME')
    password:SecretStr=Field(SecretStr(''),alias='MAIL_PASSWORD',repr=False,exclude=True)
    smtp_host:str=Field('smtp.hostinger.com',alias='MAIL_SMTP_HOST')
    smtp_port:int=Field(465,alias='MAIL_SMTP_PORT')
    smtp_secure:bool=Field(True,alias='MAIL_SMTP_SECURE')
    imap_host:str=Field('imap.hostinger.com',alias='MAIL_IMAP_HOST')
    imap_port:int=Field(993,alias='MAIL_IMAP_PORT')
    imap_secure:bool=Field(True,alias='MAIL_IMAP_SECURE')
    sync_enabled:bool=Field(True,alias='EMAIL_SYNC_ENABLED')
    sync_interval:int=Field(5,ge=5,le=60,alias='EMAIL_SYNC_INTERVAL_MINUTES')
    initial_days:int=Field(30,ge=1,le=90,alias='EMAIL_INITIAL_SYNC_DAYS')
    max_hour:int=Field(10,ge=1,le=50,alias='MAX_EMAILS_PER_HOUR')
    max_day:int=Field(100,ge=1,le=500,alias='MAX_EMAILS_PER_DAY')
    followup_days:int=Field(3,ge=1,le=30,alias='DEFAULT_FOLLOWUP_DAYS')
    outreach_sender_name:str=Field('',alias='OUTREACH_SENDER_NAME',max_length=100)
    outreach_sender_role:str=Field('',alias='OUTREACH_SENDER_ROLE',max_length=120)
    signature_name:str=Field('',alias='MAIL_SIGNATURE_NAME')
    signature_role:str=Field('',alias='MAIL_SIGNATURE_ROLE')
    website:str=Field('https://planebyte.com',alias='PLANEBYTE_WEBSITE')
    company:str=Field('PlaneByte',alias='PLANEBYTE_COMPANY_NAME')
    sending_enabled:bool=Field(False,alias='EMAIL_SENDING_ENABLED')
    tracking_base_url:str=Field('https://leads.planebyte.com/t',alias='EMAIL_TRACKING_BASE_URL')
    soft_bounce_threshold:int=Field(3,ge=1,le=10,alias='EMAIL_SOFT_BOUNCE_THRESHOLD')
    high_bounce_rate:float=Field(0.2,gt=0,le=1,alias='EMAIL_HIGH_BOUNCE_RATE')
    bounce_min_sample:int=Field(10,ge=1,alias='EMAIL_BOUNCE_MIN_SAMPLE')
    live_approved:bool=Field(False,alias='EMAIL_LIVE_APPROVED')

    gmail_username:str=Field('planebyte@gmail.com',alias='GMAIL_USERNAME')
    gmail_password:SecretStr=Field(SecretStr(''),alias='GMAIL_APP_PASSWORD',repr=False,exclude=True)
    gmail_smtp_host:str=Field('smtp.gmail.com',alias='GMAIL_SMTP_HOST')
    gmail_smtp_port:int=Field(465,alias='GMAIL_SMTP_PORT')
    gmail_smtp_secure:bool=Field(True,alias='GMAIL_SMTP_SECURE')
    gmail_imap_host:str=Field('imap.gmail.com',alias='GMAIL_IMAP_HOST')
    gmail_imap_port:int=Field(993,alias='GMAIL_IMAP_PORT')
    gmail_imap_secure:bool=Field(True,alias='GMAIL_IMAP_SECURE')
    auto_scan_enabled:bool=Field(False,alias='AUTO_SCAN_ENABLED')
    auto_email_enabled:bool=Field(False,alias='AUTO_EMAIL_ENABLED')
    tracking_enabled:bool=Field(True,alias='EMAIL_TRACKING_ENABLED')
    daily_email_target:int=Field(100,ge=1,le=500,alias='DAILY_EMAIL_TARGET')
    daily_qualified_lead_target:int=Field(100,ge=1,alias='DAILY_QUALIFIED_LEAD_TARGET')
    automation_timezone:str=Field('Asia/Kolkata',alias='AUTOMATION_TIMEZONE')

    @model_validator(mode='after')
    def select_mailbox(self):
        if self.provider not in ('gmail','hostinger'):
            raise ValueError('Unsupported email provider')
        ZoneInfo(self.automation_timezone)
        if self.provider=='gmail':
            self.username=self.gmail_username
            self.password=self.gmail_password
            self.smtp_host=self.gmail_smtp_host
            self.smtp_port=self.gmail_smtp_port
            self.smtp_secure=self.gmail_smtp_secure
            self.imap_host=self.gmail_imap_host
            self.imap_port=self.gmail_imap_port
            self.imap_secure=self.gmail_imap_secure
        return self

    @property
    def automatic_sending_enabled(self):
        return self.sending_enabled and self.auto_email_enabled

def mail_settings():return MailSettings()
