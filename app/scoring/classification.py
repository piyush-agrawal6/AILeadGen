from typing import List, Optional
from app.database.models import Business, Finding, LighthouseResult, WebsiteProfile


def recommend_service(
    business: Business,
    profile: Optional[WebsiteProfile],
    lighthouse: Optional[LighthouseResult],
    findings: List[Finding],
) -> str:
    """Recommend highest-leverage digital service based on audit findings."""
    finding_codes = {f.finding_code for f in findings}

    # 1. No website
    if not business.website or "NO_WEBSITE" in finding_codes:
        return "NEW WEBSITE + LOCAL SEO"

    # 2. Unreachable site
    if profile and not profile.reachable:
        return "WEBSITE RECOVERY + REDESIGN"

    # 3. Severe mobile / performance issues
    perf = lighthouse.performance_score if lighthouse else None
    has_no_viewport = "NO_VIEWPORT" in finding_codes
    is_very_slow = perf is not None and perf < 45.0

    if has_no_viewport or (is_very_slow and not profile.https_enabled):
        return "WEBSITE REDESIGN + PERFORMANCE OPTIMIZATION"

    # 4. Vertical specific booking funnels
    if business.vertical == "restaurant":
        if "RESTAURANT_NO_ONLINE_RESERVATION" in finding_codes or "RESTAURANT_PDF_ONLY_MENU" in finding_codes:
            if is_very_slow:
                return "WEBSITE REDESIGN + RESERVATION INTEGRATION"
            return "RESERVATION UX + LOCAL SEO"

    elif business.vertical == "hospitality":
        if "HOTEL_NO_BOOKING_ENGINE" in finding_codes:
            return "BOOKING UX + WEBSITE REDESIGN"

    elif business.vertical == "real_estate":
        if "REALESTATE_NO_LISTING_SEARCH" in finding_codes or "REALESTATE_WEAK_LEAD_FORM" in finding_codes:
            return "WEBSITE REDESIGN + MLS SEARCH INTEGRATION"

    # 5. Good performance but weak SEO
    seo_score = lighthouse.seo_score if lighthouse else None
    has_seo_issues = (
        "NO_STRUCTURED_DATA" in finding_codes
        or "MISSING_TITLE" in finding_codes
        or "MISSING_META_DESCRIPTION" in finding_codes
        or (seo_score is not None and seo_score < 70)
    )

    if has_seo_issues and (perf is None or perf >= 60):
        return "TECHNICAL SEO + LOCAL SEO"

    if has_seo_issues and is_very_slow:
        return "WEBSITE + SEO OVERHAUL"

    if is_very_slow:
        return "PERFORMANCE OPTIMIZATION"

    return "CONVERSION OPTIMIZATION + LOCAL SEO"


def generate_sales_angle(
    business: Business,
    profile: Optional[WebsiteProfile],
    lighthouse: Optional[LighthouseResult],
    findings: List[Finding],
    recommended_service: str,
) -> str:
    """Generate deterministic, human sales outreach angle from findings."""
    finding_codes = {f.finding_code for f in findings}

    if not business.website or "NO_WEBSITE" in finding_codes:
        return f"Help {business.name} launch an official mobile-friendly website to capture high-intent local customer searches."

    if profile and not profile.reachable:
        return f"Alert {business.name} that their web domain appears unreachable and propose a reliable modern rebuild."

    if business.vertical == "restaurant":
        if "RESTAURANT_PDF_ONLY_MENU" in finding_codes and "RESTAURANT_NO_ONLINE_RESERVATION" in finding_codes:
            return "Replace the non-indexable PDF menu with an interactive mobile menu and direct online table reservation flow."
        elif "RESTAURANT_PDF_ONLY_MENU" in finding_codes:
            return "Convert their mobile-unfriendly PDF menu into an SEO-indexed digital menu to boost Google local discovery."
        elif "RESTAURANT_NO_ONLINE_RESERVATION" in finding_codes:
            return "Add a frictionless 1-click table reservation widget to stop losing diners to competitors on mobile."

    elif business.vertical == "hospitality":
        if "HOTEL_NO_BOOKING_ENGINE" in finding_codes:
            return "Implement a direct booking engine to eliminate costly OTA commissions and increase direct guest reservations."
        elif "HOTEL_NO_ROOM_PAGES" in finding_codes:
            return "Upgrade room and suite showcase pages with clear availability checks to increase direct guest inquiries."

    elif business.vertical == "real_estate":
        if "REALESTATE_NO_LISTING_SEARCH" in finding_codes:
            return "Integrate an interactive property search filter and MLS feed to keep local home seekers on the site."
        elif "REALESTATE_WEAK_LEAD_FORM" in finding_codes:
            return "Add an instant home valuation lead magnet to generate exclusive seller listing inquiries."

    # General angles
    perf = lighthouse.performance_score if lighthouse else None
    if perf is not None and perf < 40.0:
        return "Resolve critical mobile speed bottlenecks to improve Google rankings and reduce bounce rates."

    if "NO_VIEWPORT" in finding_codes:
        return "Redesign layout for responsive smartphone screens to stop losing mobile prospects."

    if "NO_STRUCTURED_DATA" in finding_codes:
        return "Implement local business Schema.org rich snippets to enhance Google Maps and search result CTR."

    return "Optimize site structure, call-to-actions, and local search visibility to generate more qualified inquiries."
