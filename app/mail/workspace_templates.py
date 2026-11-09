"""Workspace-owned copy, independent of audits, AI and report generation."""
import re
from fastapi import HTTPException

def archived_template(key):
    from app.mail.templates import LEGACY_SEEDS,COMMERCIAL_IDS
    return bool(key and (key.startswith('PB_INTRO_') or key in COMMERCIAL_IDS or key in {r[0] for r in LEGACY_SEEDS}))

def require_template(c,template_id):
    from app.platform.context import organization
    if not template_id or archived_template(template_id):raise HTTPException(422,'Choose an enabled workspace-owned email template.')
    row=c.execute('SELECT id FROM email_templates WHERE id=? AND organization_id=? AND enabled=1',(template_id,organization())).fetchone()
    if not row:raise HTTPException(404,'Workspace template not found.')
    return template_id

def render_template(c,business_id,template_id):
    from app.mail.templates import render
    from app.api.organization import workspace_settings
    b=c.execute('SELECT b.*,p.organization_id FROM businesses b JOIN pipeline_runs p ON p.id=b.run_id WHERE b.id=?',(business_id,)).fetchone()
    if not b or not b['organization_id']:raise HTTPException(404,'Company not found in a workspace.')
    from app.platform.context import organization as active_organization
    organization=active_organization()
    if b['organization_id']!=organization:raise HTTPException(404,'Company not found in this workspace.')
    t=c.execute('SELECT * FROM email_templates WHERE id=? AND organization_id=? AND enabled=1',(template_id,organization)).fetchone()
    if not t or archived_template(template_id):raise HTTPException(404,'Workspace template not found.')
    profile=c.execute('SELECT o.name,p.display_name,p.contact_email FROM organizations o LEFT JOIN organization_profiles p ON p.organization_id=o.id WHERE o.id=?',(organization,)).fetchone()
    settings=workspace_settings(c,organization) or {};outreach=settings.get('outreach',{})
    signature=outreach.get('signature','') if isinstance(outreach,dict) else ''
    if not isinstance(signature,str) or len(signature)>2000:signature=''
    company=(profile['display_name'] or profile['name']) if profile else ''
    values={'business_name':b['name'],'company_name':b['name'],'website':b['website'] or '', 'city':b['city'] or '', 'vertical':b['vertical'] or '', 'sender_company':company,'sender_name':company,'signature':signature}
    subject=render(t['subject'],values);body=render(t['body_text'],values)
    if signature and '{{signature}}' not in t['body_text']:body+='\n\n'+signature
    return {**dict(t),'rendered_subject':subject,'rendered_body':body,'recommended':False,'content_version':1,'outreach_strategy':'WORKSPACE'}

def quality(c,pid,body):
    errors=[];key=body.get('template_id')
    if archived_template(key):return ['Choose a workspace-owned template; the internal experiment templates are archived.']
    if key:
        row=c.execute('SELECT t.id FROM email_templates t JOIN prospects p ON p.organization_id=t.organization_id WHERE t.id=? AND p.id=? AND t.enabled=1',(key,pid)).fetchone()
        if not row:return ['Choose an enabled template belonging to this workspace.']
    text=body.get('body_text','');subject=body.get('subject','')
    if not subject.strip() or len(text.split())<10:errors.append('Write a subject and a complete message before sending.')
    if re.search(r'{{|}}|\[INSERT|\[COMPANY',text+subject):errors.append('Resolve template placeholders before sending.')
    return errors
