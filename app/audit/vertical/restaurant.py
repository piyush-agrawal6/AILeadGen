from typing import List
from bs4 import BeautifulSoup
from app.database.models import Finding, WebsiteProfile
from app.enrichment.crawler import CrawlResult


def audit_restaurant(
    business_id: int,
    profile: WebsiteProfile,
    crawl_result: CrawlResult,
) -> List[Finding]:
    """Audit restaurant specific features: reservations, menu format, ordering, and schema."""
    findings: List[Finding] = []

    # 1. Menu Audit
    if not profile.has_menu and not crawl_result.menu_url:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_NO_MENU",
                category="VERTICAL",
                severity="HIGH",
                title="No Online Menu Detected",
                description="No food or drink menu link was detected on the crawled pages.",
                score_points=10,
            )
        )
    elif profile.menu_is_pdf:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_PDF_ONLY_MENU",
                category="VERTICAL",
                severity="MEDIUM",
                title="PDF-Only Menu Format",
                description="The restaurant menu appears to be hosted as a raw PDF file, providing poor mobile UX and zero Google-crawled menu SEO indexing.",
                evidence=profile.menu_url or crawl_result.menu_url,
                score_points=8,
            )
        )

    # 2. Reservation System Audit
    if not profile.has_booking:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_NO_ONLINE_RESERVATION",
                category="VERTICAL",
                severity="HIGH",
                title="No Online Reservation Flow Detected",
                description="No table reservation system (OpenTable, Resy, SevenRooms, direct booking widget) was detected on the pages inspected.",
                score_points=10,
            )
        )

    # 3. Online Ordering Audit
    has_ordering = False
    all_text = " ".join(crawl_result.all_htmls.values()).lower() if crawl_result.all_htmls else ""
    ordering_keywords = ["order online", "order now", "toasttab", "doordash", "ubereats", "grubhub", "chownow", "online ordering"]
    if any(k in all_text for k in ordering_keywords):
        has_ordering = True

    if not has_ordering:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_NO_ORDERING",
                category="VERTICAL",
                severity="LOW",
                title="No Online Ordering Integration Detected",
                description="No direct pickup, delivery, or online ordering funnel was found on the inspected pages.",
                score_points=5,
            )
        )

    # 4. Opening Hours
    has_hours = any(h in all_text for h in ["opening hours", "business hours", "mon -", "tue -", "wed -", "thu -", "fri -", "sat -", "sun -", "hours of operation"])
    if not has_hours:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_NO_HOURS",
                category="VERTICAL",
                severity="LOW",
                title="Opening Hours Not Prominently Displayed",
                description="No standard opening hours block was clearly detected on the homepage or contact page.",
                score_points=3,
            )
        )

    # 5. Schema check
    norm_types = {t.lower() for t in profile.schema_types}
    if not any(t in norm_types for t in ["restaurant", "foodestablishment", "cafeorcoffeeshop", "barorpub"]):
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="RESTAURANT_NO_SCHEMA",
                category="VERTICAL",
                severity="MEDIUM",
                title="Missing Restaurant Structured Data",
                description="The website does not contain schema.org/Restaurant structured data for Google Maps & rich snippet integration.",
                score_points=5,
            )
        )

    return findings
