from typing import List
from app.database.models import Finding, WebsiteProfile
from app.enrichment.crawler import CrawlResult


def audit_hospitality(
    business_id: int,
    profile: WebsiteProfile,
    crawl_result: CrawlResult,
) -> List[Finding]:
    """Audit hotel and hospitality specific features: rooms, booking engine, and lodging schema."""
    findings: List[Finding] = []
    all_text = " ".join(crawl_result.all_htmls.values()).lower() if crawl_result.all_htmls else ""

    # 1. Booking Engine
    if not profile.has_booking:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="HOTEL_NO_BOOKING_ENGINE",
                category="VERTICAL",
                severity="HIGH",
                title="No Direct Booking Engine Detected",
                description="No online booking engine or room reservation system was detected on the inspected pages.",
                score_points=12,
            )
        )

    # 2. Rooms / Accommodations
    has_rooms = any(
        w in all_text or any(w in u.lower() for u in crawl_result.all_htmls.keys())
        for w in ["/rooms", "/suites", "/accommodation", "our rooms", "room types", "guest rooms"]
    )
    if not has_rooms:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="HOTEL_NO_ROOM_PAGES",
                category="VERTICAL",
                severity="MEDIUM",
                title="Weak Room Details / Accommodation Pages",
                description="No dedicated rooms or suites showcase was detected during the crawl.",
                score_points=5,
            )
        )

    # 3. Lodging Schema
    norm_types = {t.lower() for t in profile.schema_types}
    if not any(t in norm_types for t in ["hotel", "lodgingbusiness", "motel", "hostel", "resort", "bedandbreakfast"]):
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="HOTEL_NO_SCHEMA",
                category="VERTICAL",
                severity="MEDIUM",
                title="Missing Hotel / Lodging Schema",
                description="No schema.org/Hotel or schema.org/LodgingBusiness structured data found for rich hotel search listings.",
                score_points=5,
            )
        )

    # 4. Amenities / Gallery
    has_gallery = any(w in all_text for w in ["gallery", "photos", "virtual tour", "amenities", "pool", "spa"])
    if not has_gallery:
        findings.append(
            Finding(
                business_id=business_id,
                finding_code="HOTEL_NO_GALLERY",
                category="VERTICAL",
                severity="LOW",
                title="No Dedicated Photo Gallery or Amenities Page",
                description="Visual showcase or amenity list was not clearly identified during crawl.",
                score_points=3,
            )
        )

    return findings
