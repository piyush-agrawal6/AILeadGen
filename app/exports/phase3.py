FIELDS = ["Website Opportunity", "SEO Opportunity", "Security Opportunity", "Primary Opportunity", "Secondary Opportunity", "Business Scale", "Contactability", "Lead Status", "Assigned User", "First Seen", "Last Seen"]


def metadata_values(score):
    data = score.score_breakdown if score else {}
    opportunity = data.get("opportunities", {})
    workflow = data.get("collaboration", {})
    return [opportunity.get(key) for key in ["website_opportunity_score", "seo_opportunity_score", "security_opportunity_score", "primary_opportunity", "secondary_opportunity"]] + [workflow.get("business_scale"),opportunity.get("contactability_level"),workflow.get("lead_status"),workflow.get("assigned_to"),workflow.get("first_seen_at"),workflow.get("last_seen_at")]


def safe_cell(value):
    if isinstance(value,str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def attach_workflow(conn, business_id, score):
    row = conn.execute("SELECT p.business_scale,p.lead_status,p.assigned_to,p.first_seen_at,p.last_seen_at FROM prospects p JOIN businesses b ON b.prospect_id=p.id WHERE b.id=?", (business_id,)).fetchone()
    score.score_breakdown["collaboration"] = dict(row) if row else {}
