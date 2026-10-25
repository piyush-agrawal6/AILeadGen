import logging
import re
from typing import List, Tuple
from bs4 import BeautifulSoup

from app.audit.structured_data import analyze_structured_data
from app.database.models import Finding, WebsiteProfile
from app.enrichment.crawler import CrawlResult
from app.enrichment.technology import detect_analytics, detect_technologies

logger = logging.getLogger("leadengine.audit.quick")


def perform_quick_audit(
    business_id: int,
    crawl_result: CrawlResult,
    vertical_key: str = "restaurant",
    https_enabled: bool = False,
    http_status: int = 200,
) -> Tuple[WebsiteProfile, List[Finding]]:
    """Perform fast, zero-browser static technical and SEO audit on HTML."""
    html = crawl_result.homepage_html or ""
    findings: List[Finding] = []

    profile = WebsiteProfile(
        business_id=business_id,
        requested_url=crawl_result.start_url,
        final_url=crawl_result.start_url,
        domain=crawl_result.domain,
        http_status=http_status,
        https_enabled=https_enabled,
        reachable=bool(html),
        has_robots_txt=crawl_result.has_robots_txt,
        has_sitemap=crawl_result.has_sitemap,
        page_count_crawled=crawl_result.pages_crawled,
        crawl_duration_ms=crawl_result.crawl_duration_ms,
        has_contact_page=bool(crawl_result.contact_page_url),
        contact_page_url=crawl_result.contact_page_url,
        has_booking=bool(crawl_result.booking_url),
        booking_url=crawl_result.booking_url,
        has_menu=bool(crawl_result.menu_url),
        menu_url=crawl_result.menu_url,
        menu_is_pdf=crawl_result.menu_is_pdf,
    )

    if not html:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="SITE_UNREACHABLE",
                category="WEBSITE",
                severity="HIGH",
                title="Website Unreachable",
                description="The configured business website could not be reached via standard HTTP/HTTPS requests.",
                score_points=35,
            )
        )
        return profile, findings

    soup = BeautifulSoup(html, "lxml")

    # 1. HTTPS Check
    if not https_enabled:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_HTTPS",
                category="WEBSITE",
                severity="HIGH",
                title="Missing HTTPS Encryption",
                description="The website is served over insecure HTTP without automatic redirection to HTTPS.",
                score_points=15,
            )
        )

    # 2. Viewport / Mobile Friendliness
    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    profile.has_viewport = bool(viewport_tag and viewport_tag.get("content"))
    if not profile.has_viewport:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_VIEWPORT",
                category="WEBSITE",
                severity="HIGH",
                title="Missing Mobile Viewport Meta Tag",
                description="The website lacks a responsive viewport meta tag, causing mobile browsers to render desktop scaling.",
                score_points=20,
            )
        )

    # 3. HTML Title
    title_tag = soup.find("title")
    title_text = title_tag.get_text().strip() if title_tag else ""
    profile.html_title = title_text or None
    if not title_text:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="MISSING_TITLE",
                category="SEO",
                severity="MEDIUM",
                title="Missing HTML Title Tag",
                description="The homepage does not have a <title> tag defined.",
                score_points=5,
            )
        )
    elif len(title_text) < 15:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="SHORT_TITLE",
                category="SEO",
                severity="LOW",
                title="HTML Title Too Short",
                description=f"Page title is only {len(title_text)} characters ('{title_text}'), missing descriptive keywords.",
                evidence=title_text,
                score_points=3,
            )
        )

    # 4. Meta Description
    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""
    profile.meta_description = meta_desc or None
    if not meta_desc:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="MISSING_META_DESCRIPTION",
                category="SEO",
                severity="MEDIUM",
                title="Missing Meta Description",
                description="The website does not provide a meta description for search engine result snippets.",
                score_points=4,
            )
        )

    # 5. Canonical URL
    canonical_tag = soup.find("link", rel=re.compile(r"^canonical$", re.I))
    profile.canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else None
    if not profile.canonical_url:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="MISSING_CANONICAL",
                category="SEO",
                severity="LOW",
                title="Missing Canonical URL Tag",
                description="No rel='canonical' tag found to prevent duplicate indexing.",
                score_points=2,
            )
        )

    # 6. Heading Tags (H1)
    h1_tags = soup.find_all("h1")
    profile.h1_count = len(h1_tags)
    profile.has_h1 = len(h1_tags) > 0
    if len(h1_tags) == 0:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="MISSING_H1",
                category="SEO",
                severity="MEDIUM",
                title="Missing H1 Heading",
                description="No primary <h1> heading element was found on the homepage.",
                score_points=3,
            )
        )
    elif len(h1_tags) > 2:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="MULTIPLE_H1",
                category="SEO",
                severity="LOW",
                title="Multiple H1 Headings",
                description=f"Homepage has {len(h1_tags)} H1 headings, which can dilute primary keyword signals.",
                score_points=1,
            )
        )

    # 7. OpenGraph Tags
    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    profile.has_open_graph = bool(og_title or og_image)

    # 8. Structured Data / Schema.org
    schema_present, schema_types, vert_schema = analyze_structured_data(html, vertical_key)
    profile.has_schema = schema_present
    profile.schema_types = schema_types
    if not schema_present:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_STRUCTURED_DATA",
                category="SEO",
                severity="MEDIUM",
                title="No Structured Data / Schema Found",
                description="No JSON-LD structured data was detected on the homepage.",
                score_points=6,
            )
        )
    elif not vert_schema:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_VERTICAL_SCHEMA",
                category="SEO",
                severity="MEDIUM",
                title=f"Missing Vertical-Specific {vertical_key.title()} Schema",
                description=f"Generic schema exists ({', '.join(schema_types[:3])}), but no vertical-specific {vertical_key.title()} schema was found.",
                evidence=", ".join(schema_types),
                score_points=5,
            )
        )

    # 9. Technology & Analytics Detection
    techs = detect_technologies(html)
    profile.detected_technologies = techs

    analytics = detect_analytics(html)
    profile.has_analytics = len(analytics) > 0
    profile.analytics_providers = analytics
    if not profile.has_analytics:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_DETECTABLE_ANALYTICS",
                category="WEBSITE",
                severity="LOW",
                title="No Detectable Analytics Implementation",
                description="No commonly detectable analytics implementation was found during the crawl.",
                score_points=3,
            )
        )

    # 10. Contact CTA and Contact Page
    profile.has_email_on_site = len(crawl_result.contacts.emails) > 0
    profile.has_phone_on_site = len(crawl_result.contacts.phones) > 0

    if not profile.has_contact_page:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="NO_CONTACT_PAGE",
                category="WEBSITE",
                severity="LOW",
                title="No Dedicated Contact Page",
                description="No dedicated contact or enquiry page was detected on the site.",
                score_points=5,
            )
        )

    has_cta = any(
        a.get_text().strip().lower() in ["contact us", "book now", "reserve", "call now", "order online", "get a quote", "schedule"]
        for a in soup.find_all(["a", "button"])
    )
    if not has_cta and not profile.has_booking:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="WEAK_CTA",
                category="WEBSITE",
                severity="MEDIUM",
                title="No Clear Primary Call-To-Action",
                description="No high-visibility call-to-action button (book, reserve, call, contact) was detected on the homepage.",
                score_points=6,
            )
        )

    return profile, findings
