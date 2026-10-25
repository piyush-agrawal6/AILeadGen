import logging
from typing import List, Optional
from app.database.models import Business, Finding, LeadScore, LighthouseResult, WebsiteProfile
from app.scoring.classification import generate_sales_angle, recommend_service
from app.scoring.rules import get_scoring_config

logger = logging.getLogger("leadengine.scoring.scorer")


def calculate_lead_score(
    business: Business,
    profile: Optional[WebsiteProfile],
    lighthouse: Optional[LighthouseResult],
    findings: List[Finding],
    has_valid_email: bool = False,
    has_contact_form: bool = False,
) -> LeadScore:
    """Calculate normalized 0-100 lead score across 4 pillars and assign tier and recommendation."""
    config = get_scoring_config()
    weights = config.weights
    caps = config.caps

    web_weights = weights.get("website", {})
    seo_weights = weights.get("seo", {})
    vert_weights = weights.get("vertical", {}).get(business.vertical, {})
    contact_weights = weights.get("contactability", {})

    website_raw = 0.0
    seo_raw = 0.0
    vertical_raw = 0.0
    contactability_raw = 0.0

    # 1. Evaluate Findings
    for f in findings:
        cat = f.category.upper()
        if cat == "WEBSITE":
            website_raw += f.score_points
        elif cat == "SEO":
            seo_raw += f.score_points
        elif cat == "VERTICAL":
            vertical_raw += f.score_points
        elif cat == "PERFORMANCE":
            website_raw += f.score_points

    # 2. Lighthouse metrics contribution (if available)
    if lighthouse:
        perf = lighthouse.performance_score
        if perf is not None:
            if perf < 40.0:
                website_raw += web_weights.get("performance_under_40", 20.0)
            elif perf < 60.0:
                website_raw += web_weights.get("performance_under_60", 12.0)
            elif perf < 75.0:
                website_raw += web_weights.get("performance_under_75", 5.0)

        seo = lighthouse.seo_score
        if seo is not None:
            if seo < 50.0:
                seo_raw += seo_weights.get("seo_under_50", 18.0)
            elif seo < 65.0:
                seo_raw += seo_weights.get("seo_under_65", 12.0)
            elif seo < 80.0:
                seo_raw += seo_weights.get("seo_under_80", 5.0)

    # 3. Contactability
    if has_valid_email or business.public_email:
        contactability_raw += contact_weights.get("valid_public_email", 5.0)

    if business.phone or business.normalized_phone:
        contactability_raw += contact_weights.get("business_phone", 3.0)

    if has_contact_form or (profile and profile.has_contact_page):
        contactability_raw += contact_weights.get("contact_form", 2.0)

    if business.instagram or business.facebook or business.linkedin or business.x_url:
        contactability_raw += contact_weights.get("business_social", 2.0)

    # 4. Apply Pillar Caps
    web_cap = float(caps.get("website_max", 55.0))
    seo_cap = float(caps.get("seo_max", 20.0))
    vert_cap = float(caps.get("vertical_max", 15.0))
    contact_cap = float(caps.get("contactability_max", 10.0))

    website_score = min(round(website_raw, 1), web_cap)
    seo_score = min(round(seo_raw, 1), seo_cap)
    vertical_score = min(round(vertical_raw, 1), vert_cap)
    contactability_score = min(round(contactability_raw, 1), contact_cap)

    total = round(website_score + seo_score + vertical_score + contactability_score, 1)
    total = min(max(total, 0.0), 100.0)

    tier = config.get_tier(total)
    service = recommend_service(business, profile, lighthouse, findings)
    angle = generate_sales_angle(business, profile, lighthouse, findings, service)

    breakdown = {
        "website_opportunity": website_score,
        "seo_opportunity": seo_score,
        "vertical_opportunity": vertical_score,
        "contactability": contactability_score,
        "total": total,
    }

    return LeadScore(
        business_id=business.id or 0,
        total_score=total,
        tier=tier,
        website_score=website_score,
        seo_opportunity_score=seo_score,
        vertical_opportunity_score=vertical_score,
        contactability_score=contactability_score,
        recommended_service=service,
        recommended_angle=angle,
        score_breakdown=breakdown,
    )
