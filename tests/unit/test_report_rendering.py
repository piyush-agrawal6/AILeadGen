import hashlib
import json
from pathlib import Path
import pytest
from pypdf import PdfReader
from app.reports.pdf import render_pdf,ASSETS
from app.reports.metrics import HEADER_CHECKS


def snapshot(mode='REACHABLE'):
    return {'business':{'name':'Client & Company','city':'Leeds','country':'United Kingdom','vertical':'Hospitality','website':'https://client.example','phone':'','email':''},'brand':{'name':'PlaneByte','website':'https://planebyte.com','contact_email':'contact@planebyte.com'},'mode':mode,'created_at':'2026-10-26T10:00:00+00:00','scores':{'WEBSITE':62,'SEO':97,'SECURITY':48},'primary':'SEO','website':{'https_enabled':True,'technologies':[],'schema_types':[]},'lighthouse':{'performance_score':13,'seo_score':75},'findings':[],'evidence':{'WEBSITE':[{'code':'POOR_PERFORMANCE','points':25,'detail':'Lighthouse mobile performance: 13.'}],'SEO':[{'code':'MISSING_META_DESCRIPTION','points':10,'detail':'No meta description observed.'}],'SECURITY':[{'code':code,'points':5,'detail':name+' was not observed.'} for name,code in HEADER_CHECKS]}}


def test_pdf_uses_current_scores_and_explicit_improvement_targets(tmp_path):
    p=render_pdf(snapshot(),tmp_path/'client.pdf');r=PdfReader(p);text='\n'.join(page.extract_text() for page in r.pages)
    for term in ['Website performance','CURRENT SCORE','13','75','14','Proposed target: 90/100','Target gain: +77 points','Target gain: +25 points','Target gain: +86 points','not forecasts or guarantees']:
        assert term in text
    assert len(r.pages)==9 and 'Executive summary' in r.pages[1].extract_text() and 'Current digital presence' in r.pages[2].extract_text() and 'Website experience' in r.pages[4].extract_text()
    assert all(term not in text for term in ['LeadEngine','Website opportunity','SEO opportunity','Higher opportunity score'])
    assert 'LeadEngine' not in str(r.metadata)
    assert len(r.pages[0].images)==1
    assert hashlib.sha256((ASSETS/'brand-logo.png').read_bytes()).digest()==bytes.fromhex(json.loads((ASSETS.parents[2]/'config/report_brand.json').read_text(encoding='utf-8'))['logo_sha256'])


def test_unknown_measurements_never_receive_a_target_or_gain(tmp_path):
    data=snapshot();data['lighthouse']={};data['evidence']['SECURITY']=[]
    p=render_pdf(data,tmp_path/'unknown.pdf');text=PdfReader(p).pages[1].extract_text()
    assert text.count('Not assessed')==3 and 'Target gain:' not in text


@pytest.mark.parametrize('mode',['NO_WEBSITE','UNREACHABLE'])
def test_adaptive_reports_have_no_fabricated_scores(tmp_path,mode):
    p=render_pdf(snapshot(mode),tmp_path/'adaptive.pdf');r=PdfReader(p);text='\n'.join(page.extract_text() for page in r.pages)
    assert len(r.pages)==4 and 'CURRENT SCORE' not in text and 'Target gain:' not in text
    assert 'LeadEngine' not in text


def test_logo_and_long_text_render_deterministically(tmp_path):
    data=snapshot();data['business']['name']='Long client & <literal> business name '*4;data['website']['canonical_url']='https://client.example/'+'long-url/'*40
    a=render_pdf(data,tmp_path/'one.pdf');b=render_pdf(data,tmp_path/'two.pdf')
    assert a.read_bytes()==b.read_bytes()
    r=PdfReader(a);assert '<literal>' in r.pages[0].extract_text() and 'Executive summary' in r.pages[1].extract_text()

def test_stored_capture_and_configurable_offer(tmp_path):
    from PIL import Image
    image=tmp_path/'stored.png';Image.new('RGB',(1440,900),'#eeeeee').save(image)
    data=snapshot();data['_capture_path']=str(image);data['capture']={'captured_at':data['created_at'],'status':'READY'}
    data['offer']={'enabled':True,'title':'Website project package','subtitle':'Included at no additional charge','seo':True,'security':False,'support':False}
    pdf=PdfReader(render_pdf(data,tmp_path/'with-image.pdf'))
    assert len(pdf.pages[2].images)==2 # Brand mark plus the stored homepage image.
    text='\n'.join(page.extract_text() for page in pdf.pages)
    assert 'SEO launch foundations' in text and 'Post-launch support' not in text
    assert '£' not in text and '$' not in text
    assert 'Public homepage captured' in text
