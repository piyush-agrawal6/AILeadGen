import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.database.models import Business, Finding, LeadScore, LighthouseResult, WebsiteProfile

COLUMNS = [
    "Rank",
    "Score",
    "Tier",
    "Business",
    "Vertical",
    "City",
    "State",
    "Country",
    "Website",
    "Website Status",
    "Email",
    "Email Status",
    "Phone",
    "Contact Form",
    "Instagram",
    "Facebook",
    "LinkedIn",
    "Performance",
    "SEO",
    "Accessibility",
    "Best Practices",
    "Main Problems",
    "Recommended Service",
    "Sales Angle",
    "Technologies",
    "Schema Types",
    "Source",
    "Confidence",
    "Audit Date",
]


def clean_val(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def export_leads_to_csv(
    leads: List[Tuple[Business, LeadScore, Optional[WebsiteProfile], Optional[LighthouseResult], List[Finding]]],
    output_path: Path,
) -> Path:
    """Export ranked leads to a CSV file with readable pipe-separated lists."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)

        for rank, item in enumerate(leads, start=1):
            business, score, profile, lh, findings = item

            # Website status
            if not business.website:
                web_status = "NO_WEBSITE"
            elif profile and profile.reachable:
                web_status = "REACHABLE"
            else:
                web_status = "UNREACHABLE"

            # Email & status
            email = clean_val(business.public_email)
            email_status = "FOUND" if email else "NONE"

            # Phone
            phone = clean_val(business.normalized_phone or business.phone)

            # Top 3-5 main problems
            top_problems = " | ".join(f.title for f in findings[:5]) if findings else "None detected"

            # Tech & schema
            techs = " | ".join(profile.detected_technologies) if profile and profile.detected_technologies else ""
            schemas = " | ".join(profile.schema_types) if profile and profile.schema_types else ""

            # Sources
            sources = []
            if business.source_overture:
                sources.append("Overture")
            if business.source_osm:
                sources.append("OSM")
            source_str = " + ".join(sources) if sources else "Direct"

            row = [
                rank,
                score.total_score,
                score.tier,
                business.name,
                business.vertical,
                clean_val(business.city),
                clean_val(business.state),
                clean_val(business.country),
                clean_val(business.website),
                web_status,
                email,
                email_status,
                phone,
                profile.contact_page_url if profile and profile.contact_page_url else "",
                clean_val(business.instagram),
                clean_val(business.facebook),
                clean_val(business.linkedin),
                lh.performance_score if lh and lh.performance_score is not None else "",
                lh.seo_score if lh and lh.seo_score is not None else "",
                lh.accessibility_score if lh and lh.accessibility_score is not None else "",
                lh.best_practices_score if lh and lh.best_practices_score is not None else "",
                top_problems,
                score.recommended_service,
                score.recommended_angle,
                techs,
                schemas,
                source_str,
                f"{business.source_confidence:.2f}",
                score.calculated_at or business.updated_at or "",
            ]
            writer.writerow(row)

    return output_path
