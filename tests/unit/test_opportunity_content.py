from test_phase4 import workspace
import copy,json
from pathlib import Path
from app.reports.opportunity import plan,report_issues,email_values
from app.mail.templates import render,COMMERCIAL_BODY
from app.mail.quality import validate_pdf
from app.reports.pdf import render_pdf
from pypdf import PdfReader

def data():
 brand=json.loads(Path('config/report_brand.json').read_text())
 return {'business':{'name':'Homestay Hotels','city':'Greater London','country':'United Kingdom','vertical':'Hospitality','website':'http://business.example'},'brand':brand,'created_at':'2026-11-01T10:00:00+00:00','mode':'REACHABLE','primary':'WEBSITE','scores':{'WEBSITE':83,'SEO':58,'SECURITY':88},'lighthouse':{},'website':{},'findings':[], 'offer':{'enabled':True,'seo':True,'security':True,'support':True},'evidence':{'WEBSITE':[{'code':'HTTP_ONLY','points':30,'detail':'The final website response uses HTTP.'},{'code':'NO_MOBILE_VIEWPORT','points':20,'detail':'No viewport declaration in observed HTML.'},{'code':'NO_PRIMARY_CTA','points':15,'detail':'No vertical conversion CTA among observed links.'}],'SEO':[{'code':'NO_MOBILE_VIEWPORT','points':8,'detail':'Mobile viewport absent.'},{'code':'MISSING_META_DESCRIPTION','points':10,'detail':'Description absent.'}],'SECURITY':[{'code':'HTTP_ONLY','points':30,'detail':'HTTP response.'}]}}

def test_commercial_email_is_specific_short_and_conditional():
 d=data();p=plan(d);values=email_values(d,p);body=render(COMMERCIAL_BODY,values)
 assert 100<=len(body.split())<=170
 for value in ('Homestay Hotels','guest-journey perspective','encrypted connection','smaller screens','can affect','PlaneByte','SEO launch foundations','reply here','Software Engineering · SEO · Security'):assert value in body
 assert not report_issues(d)
 d['offer']['enabled']=False
 assert not plan(d)['included'] and 'add-ons' not in render(COMMERCIAL_BODY,email_values(d,plan(d)))

def test_deduplication_and_no_invented_evidence():
 d=data();p=plan(d)
 assert len([r for r in p['findings'] if r['code']=='HTTP_ONLY'])==1
 assert len([r for r in p['findings'] if r['code']=='NO_MOBILE_VIEWPORT'])==1
 d['evidence']={'WEBSITE':[]}
 assert report_issues(d) and not plan(d)['findings']
 d=data();d['business']['name']='{{company}}'
 assert any('placeholders' in x for x in report_issues(d))

def test_eight_page_pdf_leads_with_opportunities_and_only_one_explanation(tmp_path):
 d=data();p=render_pdf(d,tmp_path/'review.pdf');assert validate_pdf(p.read_bytes())==8
 pages=PdfReader(p).pages;text='\n'.join(page.extract_text() for page in pages)
 assert 'Executive Opportunity Brief' in pages[0].extract_text()
 assert 'SEO launch foundations' in pages[0].extract_text()
 assert 'What We Found' in pages[1].extract_text()
 assert 'Not assessed' not in text and 'Target gain' not in text
 assert text.count('the page we reached was served over HTTP')+text.count('The page we reached was served over HTTP')==1
 assert 'REPLY TO THE EMAIL' in text and 'contact@planebyte.com' in text
 assert not any(x in text for x in ('300%','lost revenue','FREE AUDIT'))
 assert p.read_bytes()==render_pdf(d,tmp_path/'same.pdf').read_bytes()


def test_human_identity_falls_back_and_uses_only_configured_values():
 from app.mail.config import MailSettings
 from app.reports.opportunity import company_signature,email_values,why_planebyte
 d=data();p=plan(d)
 blank=MailSettings(_env_file=None,OUTREACH_SENDER_NAME='',OUTREACH_SENDER_ROLE='Unattributed role')
 assert company_signature(d,blank).startswith('PlaneByte\nSoftware Engineering')
 assert 'Unattributed role' not in company_signature(d,blank)
 person=MailSettings(_env_file=None,OUTREACH_SENDER_NAME='Configured Person',OUTREACH_SENDER_ROLE='Project Lead')
 assert company_signature(d,person).startswith('Configured Person | PlaneByte\nProject Lead\n')
 body=render(COMMERCIAL_BODY,email_values(d,p,person))
 assert 'while researching' not in body and 'viewport' not in body and 'HTML' not in body
 assert 'priority order and rough implementation scope' in body
 assert 'one technical team' in why_planebyte(p)[2]


def test_first_contact_requires_two_findings_specific_opening_value_and_concrete_reply(workspace,monkeypatch):
 from app.mail import quality
 from app.reports.opportunity import email_observation
 from app.database.prospects import now
 c,b,pid,settings,_=workspace
 d=data();d['business']['name']=b.name;d['sales_review']=plan(d)
 report_id='quality-report'
 c.execute("INSERT INTO client_reports(id,prospect_id,business_id,created_at,created_by,version,status,object_key,snapshot_json,updated_at) VALUES(?,?,?,?,?,1,'READY','quality.pdf',?,?)",(report_id,pid,b.id,now(),'system',json.dumps(d),now()))
 values=email_values(d,plan(d),settings)
 body={'subject':values['opportunity_subject'],'body_text':render(COMMERCIAL_BODY,values),'report_id':report_id,'template_id':'combined','message_type':'FIRST_CONTACT'}
 monkeypatch.setattr(quality,'mail_settings',lambda:settings)
 assert quality.archived_issues(c,pid,body)==[]
 one={**values,'observations':email_observation(plan(d)['top'][0],d['business'])+'.'}
 assert any('two meaningful' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,one)}))
 assert any('included value' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,{**values,'included_value':''})}))
 assert any('company-specific' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,{**values,'opening':'While researching businesses in your area, we noticed a few points.'})}))
 assert any('configured next step' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,{**values,'cta':"Reply and we'll outline what we'd prioritise first."})}))

 assert any('business consequence' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,{**values,'business_impact':''})}))
 assert any('specific PlaneByte solution' in e for e in quality.archived_issues(c,pid,{**body,'body_text':render(COMMERCIAL_BODY,{**values,'solution':''})}))


def test_vertical_journey_copy_uses_business_context_without_list_language():
 for vertical,expected in [('Hospitality','guest-journey'),('Dentists','patient-journey'),('Real Estate','buyer or tenant-journey'),('Home Services','customer-journey'),('Legal','client-journey')]:
  d=data();d['business']['vertical']=vertical;values=email_values(d,plan(d));body=render(COMMERCIAL_BODY,values)
  assert expected in body
  assert not any(term in body.lower() for term in ('while researching','viewport declaration','reviewed html','csp','hsts'))
  assert 'priority order and rough implementation scope' in body
