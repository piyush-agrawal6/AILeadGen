import pytest
from app.database.models import Business, Finding, LighthouseResult, WebsiteProfile
from app.scoring.classification import generate_sales_angle, recommend_service
from app.scoring.rules import get_scoring_config
from app.scoring.scorer import calculate_lead_score


def test_no_website_lead_scoring():
    b = Business(
        id=1,
        name="Artisan Oak Bakery",
        normalized_name="artisan oak bakery",
        vertical="restaurant",
        website=None,
        phone="512-555-9988",
        public_email="contact@artisanoak.com",
    )
    findings = [
        Finding(
            business_id=1,
            finding_code="NO_WEBSITE",
            category="WEBSITE",
            severity="HIGH",
            title="No Public Website Found",
            description="No website detected.",
            score_points=40,
        )
    ]
    lead_score = calculate_lead_score(
        business=b,
        profile=None,
        lighthouse=None,
        findings=findings,
        has_valid_email=True,
    )

    # 40 (website) + 5 (email) + 3 (phone) = 48 -> Tier C or B
    assert lead_score.website_score == 40.0
    assert lead_score.contactability_score >= 8.0
    assert lead_score.total_score >= 48.0
    assert lead_score.recommended_service == "NEW WEBSITE + LOCAL SEO"
    assert "launch an official mobile-friendly website" in lead_score.recommended_angle


def test_high_opportunity_lead_scoring_and_caps():
    b = Business(
        id=2,
        name="Pasta Palace",
        normalized_name="pasta palace",
        vertical="restaurant",
        website="http://pastapalace.com",
        phone="512-555-1234",
        public_email="manager@pastapalace.com",
    )
    profile = WebsiteProfile(
        business_id=2,
        requested_url="http://pastapalace.com",
        https_enabled=False,
        has_viewport=False,
        has_schema=False,
    )
    lh = LighthouseResult(
        business_id=2,
        performance_score=28.0,
        seo_score=42.0,
    )
    findings = [
        Finding(business_id=2, finding_code="NO_HTTPS", category="WEBSITE", severity="HIGH", title="No HTTPS", score_points=15),
        Finding(business_id=2, finding_code="NO_VIEWPORT", category="WEBSITE", severity="HIGH", title="No Viewport", score_points=20),
        Finding(business_id=2, finding_code="RESTAURANT_PDF_ONLY_MENU", category="VERTICAL", severity="MEDIUM", title="PDF Menu", score_points=8),
        Finding(business_id=2, finding_code="RESTAURANT_NO_ONLINE_RESERVATION", category="VERTICAL", severity="HIGH", title="No Reservation", score_points=10),
        Finding(business_id=2, finding_code="NO_STRUCTURED_DATA", category="SEO", severity="MEDIUM", title="No Schema", score_points=6),
    ]

    lead_score = calculate_lead_score(
        business=b,
        profile=profile,
        lighthouse=lh,
        findings=findings,
        has_valid_email=True,
    )

    # Check that individual caps hold:
    assert lead_score.website_score <= 55.0
    assert lead_score.seo_opportunity_score <= 20.0
    assert lead_score.vertical_opportunity_score <= 15.0
    assert lead_score.contactability_score <= 10.0
    assert lead_score.total_score <= 100.0

    # With so many severe issues, this should be an A+ or A lead
    assert lead_score.tier in ("A+", "A")
    assert lead_score.total_score >= 70.0


def test_service_recommendation_and_sales_angle():
    b = Business(
        id=3,
        name="Grand Azure Hotel",
        normalized_name="grand azure hotel",
        vertical="hospitality",
        website="https://grandazure.com",
    )
    profile = WebsiteProfile(business_id=3, requested_url="https://grandazure.com", reachable=True)
    findings = [
        Finding(
            business_id=3,
            finding_code="HOTEL_NO_BOOKING_ENGINE",
            category="VERTICAL",
            severity="HIGH",
            title="No Direct Booking Engine",
            description="No direct booking.",
            score_points=12,
        )
    ]
    service = recommend_service(b, profile, None, findings)
    assert "BOOKING" in service
    angle = generate_sales_angle(b, profile, None, findings, service)
    assert "direct booking engine" in angle.lower()
