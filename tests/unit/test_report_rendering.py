import hashlib,json
from pathlib import Path
import pytest
from pypdf import PdfReader
from app.reports.pdf import render_pdf,ASSETS
from app.reports.metrics import HEADER_CHECKS

def snapshot(mode='REACHABLE'):
 return {'business':{'name':'Client & Company','city':'Leeds','country':'United Kingdom','vertical':'Hospitality','website':'https://client.example','phone':'','email':''},'brand':json.loads(Path('config/report_brand.json').read_text()),'mode':mode,'created_at':'2026-10-26T10:00:00+00:00','scores':{'WEBSITE':62,'SEO':97,'SECURITY':48},'primary':'SEO','website':{'https_enabled':True,'technologies':[],'schema_types':[]},'lighthouse':{'performance_score':13,'seo_score':75},'findings':[],'evidence':{'WEBSITE':[{'code':'POOR_PERFORMANCE','points':25,'detail':'Lighthouse mobile performance: 13.'}],'SEO':[{'code':'MISSING_META_DESCRIPTION','points':10,'detail':'No meta description observed.'}],'SECURITY':[{'code':code,'points':5,'detail':name+' was not observed.'} for name,code in HEADER_CHECKS]}}

def text_of(data,tmp_path):
 r=PdfReader(render_pdf(data,tmp_path/'client.pdf'));return r,'\n'.join(page.extract_text() for page in r.pages)

def test_report_leads_with_opportunities_and_only_measured_scores(tmp_path):
 r,text=text_of(snapshot(),tmp_path)
 assert len(r.pages)==8
 for term in ['Executive Opportunity Brief','What We Found','Lighthouse mobile performance: 13','Lighthouse SEO: 75','What We Would Improve','REPLY TO THE EMAIL']:assert term in text
 assert not any(term in text for term in ('Target gain','Not assessed','LeadEngine','CURRENT SCORE'))
 assert 'LeadEngine' not in str(r.metadata)
 assert len(r.pages[0].images)==1
 assert hashlib.sha256((ASSETS/'brand-logo.png').read_bytes()).hexdigest()==json.loads(Path('config/report_brand.json').read_text())['logo_sha256']

def test_unknown_measurements_are_omitted(tmp_path):
 d=snapshot();d['lighthouse']={};d['evidence']['SECURITY']=[]
 _,text=text_of(d,tmp_path)
 assert 'Not assessed' not in text and 'RECORDED MEASUREMENTS' not in text and 'Target gain:' not in text

@pytest.mark.parametrize('mode',['NO_WEBSITE','UNREACHABLE'])
def test_adaptive_reports_have_no_fabricated_scores(tmp_path,mode):
 _,text=text_of(snapshot(mode),tmp_path)
 assert 'RECORDED MEASUREMENTS' not in text and 'Target gain:' not in text
 assert 'No meta description observed' not in text

def test_logo_and_long_text_render_deterministically(tmp_path):
 d=snapshot();d['business']['name']='Long client & <literal> business name '*4
 a=render_pdf(d,tmp_path/'one.pdf');b=render_pdf(d,tmp_path/'two.pdf')
 assert a.read_bytes()==b.read_bytes()
 assert '<literal>' in PdfReader(a).pages[0].extract_text()

def test_configurable_offer_has_no_unapproved_inclusions(tmp_path):
 d=snapshot();d['primary']='WEBSITE';d['offer']={'enabled':True,'seo':True,'security':False,'support':False}
 _,text=text_of(d,tmp_path)
 assert 'SEO launch foundations' in text and 'Post-launch technical validation · INCLUDED' not in text
 assert '$' not in text and '£' not in text
