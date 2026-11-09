import json,uuid
from unittest.mock import Mock,AsyncMock
import pytest
from fastapi import HTTPException
from test_people import owned,seed
from app.platform.context import workspace_scope
from app.people import service
from app.people.extraction import extract_people
from app.people.verification import check
from app.intelligence import jobs
from app.enrichment.crawler import CrawlResult

HTML='''<html><title>Controlled Dentistry</title><script type="application/ld+json">{"@type":"Organization","name":"Controlled Dentistry 1","employee":[{"@type":"Person","name":"Avery Example","jobTitle":"CTO","email":"avery@controlled.example","sameAs":"https://controlled.example/team/avery"},{"@type":"Person","name":"Morgan Example","jobTitle":"Founder"}]}</script></html>'''
async def crawl(self,url):
 r=CrawlResult(url);r.pages_crawled=1;r.all_htmls={url:HTML};r.homepage_html=HTML;return r

def test_contacts_discovery_jobs_are_owned_idempotent_and_preserve_manual_facts(owned,monkeypatch):
 c,path,org,other=owned;mock=AsyncMock(side_effect=crawl);monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',lambda self,url:mock(self,url))
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);body=jobs.Start(kind='CONTACT_DISCOVER',resource_ids=[str(b.id)]);job=jobs.create(c,body);c.commit();assert jobs.create(c,body)['id']==job['id'];c.commit()
  jobs.execute(job['id'],path);result=jobs.detail(c,job['id']);assert result['status']=='COMPLETED' and result['counts']['COMPLETE']==1
  assert service.listing(c,business_id=b.id)['total']==2 and mock.await_count==1
  jobs.execute(job['id'],path);assert mock.await_count==1
  assert result['usage']['monetary_cost'] is None
  for table in ('email_messages','lighthouse_results','client_reports','findings'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  with pytest.raises(HTTPException) as denied:jobs.detail(c,job['id'])
  assert denied.value.status_code==404
  with pytest.raises(HTTPException):jobs.create(c,jobs.Start(kind='CONTACT_DISCOVER',resource_ids=[str(b.id)]))
  with pytest.raises(HTTPException):jobs.execute(job['id'],path)
 assert mock.await_count==1

def test_verification_records_mx_not_deliverability_and_contact_revisions_are_safe(owned,monkeypatch):
 c,path,org,_=owned
 monkeypatch.setattr('app.people.verification.check',lambda email:{'state':'MX_AVAILABLE','mx_available':True,'recipient_delivery_verified':False})
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);contact=service.save(c,b.id,service.Person(name='Avery Example',work_email='avery@controlled.example'));c.commit()
  job=jobs.create(c,jobs.Start(kind='CONTACT_VERIFY',resource_ids=[contact['id']]));c.commit();jobs.execute(job['id'],path)
  result=service.get(c,contact['id']);assert result['verification_state']=='MX_AVAILABLE' and result['recipient_delivery_verified'] is False and result['revision']==2
  result=service.save(c,b.id,service.Person(name=result['name'],work_email=result['work_email'],revision=2),result['id']);assert result['evidence']['verification']['mx_available']
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_cancel_retry_partial_failure_and_domain_first_cache(owned,monkeypatch):
 c,path,org,_=owned;calls=AsyncMock(side_effect=crawl);monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',lambda self,url:calls(self,url))
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);job=jobs.create(c,jobs.Start(kind='COMPANY_ENRICH',resource_ids=[str(b.id)]));c.commit();jobs.execute(job['id'],path)
  next_job=jobs.create(c,jobs.Start(kind='COMPANY_ENRICH',resource_ids=[str(b.id)]));c.commit();jobs.execute(next_job['id'],path)
  assert calls.await_count==1 and jobs.detail(c,next_job['id'])['items'][0]['result']['mode']=='CACHED'
  cancelled=jobs.create(c,jobs.Start(kind='COMPANY_ENRICH',resource_ids=[str(b.id)],reuse_days=0));jobs.control(c,cancelled['id'],'cancel');c.commit();jobs.execute(cancelled['id'],path);assert calls.await_count==1
  failure=jobs.create(c,jobs.Start(kind='COMPANY_ENRICH',resource_ids=[str(b.id)],reuse_days=0));c.commit();calls.side_effect=RuntimeError('Fixture provider failure');jobs.execute(failure['id'],path)
  assert jobs.detail(c,failure['id'])['status']=='PARTIAL'
  calls.side_effect=crawl;jobs.control(c,failure['id'],'retry');c.commit();jobs.execute(failure['id'],path);assert jobs.detail(c,failure['id'])['status']=='COMPLETED'

def test_public_extractor_does_not_invent_people_or_infer_employment():
 assert extract_people({'https://company.example':'<h1>Contact our CTO</h1>'},'Controlled Dentistry 1')==[]
 assert extract_people({'https://company.example':'<script type="application/ld+json">{"@type":"Person","name":"Other Person","jobTitle":"CEO","worksFor":{"name":"Other company"}}</script>'},'Controlled Dentistry 1')==[]
 assert len(extract_people({'https://company.example':HTML},'Controlled Dentistry 1'))==2

def test_dns_verification_distinguishes_null_mx_domain_fallback_and_uncertainty(monkeypatch):
 import dns.resolver
 resolver=Mock();monkeypatch.setattr('app.people.verification.dns.resolver.Resolver',lambda:resolver)
 resolver.resolve.return_value=[Mock(exchange='mail.example.')];assert check('info@controlled.example')['state']=='MX_AVAILABLE'
 resolver.resolve.return_value=[Mock(exchange='.')];assert check('info@controlled.example')['state']=='INVALID'
 resolver.resolve.side_effect=[dns.resolver.NoAnswer(),['192.0.2.1']];result=check('info@controlled.example');assert result['state']=='DOMAIN_VALID' and result['mx_available'] is False
 resolver.resolve.side_effect=dns.resolver.Timeout();assert check('info@controlled.example')['state']=='UNCERTAIN'
 assert check('invalid')['state']=='INVALID'


def test_contact_discovery_cache_and_negative_results_prevent_repeat_crawls(owned,monkeypatch):
 c,path,org,_=owned;calls=AsyncMock(side_effect=crawl);monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',lambda self,url:calls(self,url))
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org)
  for _ in range(2):
   job=jobs.create(c,jobs.Start(kind='CONTACT_DISCOVER',resource_ids=[str(b.id)]));c.commit();jobs.execute(job['id'],path)
  result=jobs.detail(c,job['id']);assert result['items'][0]['result']['mode']=='CACHED' and calls.await_count==1
  person=service.listing(c,business_id=b.id)['items'][0];assert person['evidence']['origin']=='PUBLIC_COMPANY_STRUCTURED_DATA'
  service.archive(c,person['id'],person['revision']);c.commit()
  with pytest.raises(HTTPException):jobs.create(c,jobs.Start(kind='CONTACT_ENRICH',resource_ids=[person['id']]))
