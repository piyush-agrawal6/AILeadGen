"""Fail-closed first-contact content checks; transport and engagement stay unchanged."""
from app.mail.config import mail_settings

def issues(c,pid,body,*,settings=None):
 if body.get('message_type','FIRST_CONTACT')!='FIRST_CONTACT':return []
 if body.get('outreach_strategy')=='FIXED_5' or body.get('experiment_member_id'):return ['Internal experiment messages are archived; choose a workspace-owned template.']
 from app.mail.workspace_templates import quality
 return quality(c,pid,body)

def archived_issues(c,pid,body,*,settings=None):
 """Compatibility for saved assessment consumers; never the send quality gate."""
 from app.search_visibility.report_quality import issues as archived
 return archived(c,pid,body,settings=settings or mail_settings())

def validate_pdf(content,report_type="FULL_AUDIT"):
 from app.search_visibility.report_quality import validate_pdf as validate
 return validate(content,report_type)
