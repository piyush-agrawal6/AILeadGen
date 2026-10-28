import pytest
from app.database.models import Business, WebsiteProfile, LighthouseResult
from app.enrichment.crawler import CrawlResult
from app.enrichment.http_probe import ProbeResult
from app.scoring.opportunities import analyze_opportunities, classify_scale


def business(**kwargs):
    return Business(id=1, name="Independent Dental", normalized_name="independent dental", vertical="dentists", city="Austin", **kwargs)


def test_no_website_is_website_opportunity_without_invented_seo_security():
    result = analyze_opportunities(business(phone="+15125551234"))
    assert result["website_opportunity_score"] == 95
    assert result["seo_opportunity_score"] is None
    assert result["security_opportunity_score"] is None
    assert result["primary_opportunity"] == "WEBSITE"
    assert result["contactability_level"] == "MEDIUM"


def test_shared_html_security_and_seo_evidence():
    b = business(website="https://dental.example", public_email="info@dental.example", phone="+15125551234")
    crawl = CrawlResult(b.website)
    crawl.all_htmls[b.website] = '<html><meta name="robots" content="noindex"><script src="http://cdn.example/x.js"></script><form action="http://dental.example/contact"></form></html>'
    profile = WebsiteProfile(business_id=1, requested_url=b.website, reachable=True, https_enabled=True)
    probe = ProbeResult(requested_url=b.website, reachable=True, response_headers={"server": "nginx/1.24.0", "x-powered-by": "PHP"}, cookies=["session=abc"])
    result = analyze_opportunities(b, profile, None, crawl, probe)
    assert result["seo_opportunity_score"] >= 70
    assert result["security_opportunity_score"] >= 60
    assert result["primary_opportunity"] == "SEO"
    assert result["secondary_opportunity"] == "SECURITY"
    assert result["contactability_level"] == "HIGH"
    codes = {item["code"] for item in result["evidence"]["SECURITY"]}
    assert {"MIXED_ACTIVE_CONTENT", "INSECURE_FORM_ACTION", "SESSION_COOKIE_NO_HTTPONLY"} <= codes


def test_good_website_has_low_opportunity():
    b = business(website="https://dental.example", phone="+15125551234")
    crawl = CrawlResult(b.website)
    crawl.all_htmls[b.website] = '<h1>Austin Dental</h1><p>Monday opening hours</p><a href="/book">Book now</a><a href="/services">Services</a><a href="/treatments">Treatments</a><a href="/locations">Locations</a><a href="tel:+15125551234">Call</a><a href="/contact">Contact</a>'
    profile = WebsiteProfile(business_id=1, requested_url=b.website, reachable=True, https_enabled=True, has_viewport=True, html_title="Austin Independent Dental", meta_description="Local dental services", has_h1=True, h1_count=1, canonical_url=b.website, has_robots_txt=True, has_sitemap=True, has_schema=True, schema_types=["Dentist"], has_contact_page=True)
    headers = {"strict-transport-security":"max-age=63072000", "content-security-policy":"default-src 'self'; frame-ancestors 'none'", "x-content-type-options":"nosniff", "referrer-policy":"strict-origin", "permissions-policy":"camera=()"}
    result = analyze_opportunities(b, profile, LighthouseResult(business_id=1, performance_score=95), crawl, ProbeResult(requested_url=b.website,response_headers=headers))
    assert result["website_opportunity_score"] == result["seo_opportunity_score"] == result["security_opportunity_score"] == 0
    assert result["primary_opportunity"] is None


def test_selected_opportunities_control_primary():
    result = analyze_opportunities(business(), selected=["SEO"])
    assert result["primary_opportunity"] is None


def test_location_count_requires_corroborating_scale_signals():
    b = business(domain="dental.example")
    assert classify_scale(b, 20, 1)[0] == "SMALL_GROUP"
    assert classify_scale(b, 20, 3)[0] == "ENTERPRISE"
    assert classify_scale(b, 8, 2)[0] == "REGIONAL"


def test_known_chain_domain():
    assert classify_scale(business(domain="mcdonalds.com"))[0] == "KNOWN_CHAIN"
