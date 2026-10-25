from typing import List
from app.database.models import Finding, WebsiteProfile
from app.enrichment.crawler import CrawlResult


def audit_real_estate(
    business_id: int,
    profile: WebsiteProfile,
    crawl_result: CrawlResult,
) -> List[Finding]:
    """Audit real estate agency features: MLS/property search, enquiry forms, and agent schema."""
    findings: List[Finding] = []
    all_text = " ".join(crawl_result.all_htmls.values()).lower() if crawl_result.all_htmls else ""

    # 1. Property search / listings
    has_listings = any(
        w in all_text or any(w in u.lower() for u in crawl_result.all_htmls.keys())
        for w in ["property search", "search homes", "featured listings", "/properties", "/listings", "idx", "mls"]
    )
    if not has_listings:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="REALESTATE_NO_LISTING_SEARCH",
                category="VERTICAL",
                severity="HIGH",
                title="No Interactive Property Search / Listings Found",
                description="No interactive MLS or property search filter was detected on the inspected pages.",
                score_points=10,
            )
        )

    # 2. Lead capture / valuation form
    has_lead_form = any(
        w in all_text
        for w in ["home valuation", "what is my home worth", "request a valuation", "schedule a viewing", "buyer consultation"]
    )
    if not has_lead_form:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="REALESTATE_WEAK_LEAD_FORM",
                category="VERTICAL",
                severity="MEDIUM",
                title="Missing Home Valuation / Buyer Lead Funnel",
                description="No high-converting lead magnet (e.g. instant home valuation, viewing scheduler) was detected.",
                score_points=8,
            )
        )

    # 3. Agent / Team page
    has_agents = any(
        w in all_text or any(w in u.lower() for u in crawl_result.all_htmls.keys())
        for w in ["/agents", "/team", "/our-agents", "meet the team", "our brokers"]
    )
    if not has_agents:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="REALESTATE_NO_AGENT_PAGES",
                category="VERTICAL",
                severity="LOW",
                title="No Dedicated Agent / Broker Profiles Found",
                description="No individual agent bio or contact pages were identified during the crawl.",
                score_points=4,
            )
        )

    # 4. Schema
    norm_types = {t.lower() for t in profile.schema_types}
    if not any(t in norm_types for t in ["realestateagent", "realestateagency", "realestatelisting"]):
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="REALESTATE_NO_SCHEMA",
                category="VERTICAL",
                severity="MEDIUM",
                title="Missing RealEstateAgent Schema",
                description="No schema.org/RealEstateAgent structured data found for local real estate search integration.",
                score_points=5,
            )
        )

    return findings
