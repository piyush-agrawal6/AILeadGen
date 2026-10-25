from pathlib import Path
from typing import List, Optional
from app.database.models import Business, Finding, LeadScore, LighthouseResult, WebsiteProfile

REPORTS_DIR = Path("output/reports")


def generate_html_report(
    business: Business,
    score: LeadScore,
    profile: Optional[WebsiteProfile],
    lh: Optional[LighthouseResult],
    findings: List[Finding],
) -> Path:
    """Generate a clean, standalone HTML audit & prospecting report for an individual business."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in business.name.lower())[:30]
    out_file = REPORTS_DIR / f"{business.id}_{safe_name}.html"

    tier_colors = {
        "A+": "#16a34a",
        "A": "#0284c7",
        "B": "#d97706",
        "C": "#dc2626",
        "D": "#64748b",
    }
    tier_color = tier_colors.get(score.tier, "#475569")

    # Findings HTML
    findings_html = ""
    for f in findings:
        sev_color = "#ef4444" if f.severity == "HIGH" else ("#f59e0b" if f.severity == "MEDIUM" else "#3b82f6")
        evidence_html = f"<div class='evidence'><strong>Evidence:</strong> {f.evidence}</div>" if f.evidence else ""
        findings_html += f"""
        <div class="finding-card">
            <div class="finding-header">
                <span class="badge" style="background-color: {sev_color}">{f.severity}</span>
                <span class="finding-title">{f.title}</span>
                <span class="points">+{f.score_points} pts</span>
            </div>
            <p class="finding-desc">{f.description}</p>
            {evidence_html}
        </div>
        """

    # Metrics HTML
    perf_val = f"{lh.performance_score:.0f}" if lh and lh.performance_score is not None else "N/A"
    seo_val = f"{lh.seo_score:.0f}" if lh and lh.seo_score is not None else "N/A"
    a11y_val = f"{lh.accessibility_score:.0f}" if lh and lh.accessibility_score is not None else "N/A"
    bp_val = f"{lh.best_practices_score:.0f}" if lh and lh.best_practices_score is not None else "N/A"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeadEngine Audit Report — {business.name}</title>
    <style>
        :root {{
            --primary: #0f172a;
            --accent: #2563eb;
            --bg: #f8fafc;
            --card: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --text-muted: #64748b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 32px 16px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            background: var(--card);
            padding: 32px;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 26px;
            color: var(--primary);
        }}
        .header .meta {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .score-pill {{
            text-align: center;
            background: {tier_color}15;
            border: 2px solid {tier_color};
            border-radius: 12px;
            padding: 12px 24px;
        }}
        .score-num {{
            font-size: 36px;
            font-weight: 800;
            color: {tier_color};
            line-height: 1;
        }}
        .score-tier {{
            font-size: 14px;
            font-weight: 700;
            color: {tier_color};
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--card);
            padding: 24px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }}
        .card h2 {{
            margin: 0 0 16px 0;
            font-size: 16px;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .item {{
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .item strong {{
            color: var(--text-muted);
            display: inline-block;
            width: 110px;
        }}
        .highlight-box {{
            background: #eff6ff;
            border-left: 4px solid var(--accent);
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 24px;
        }}
        .highlight-box h3 {{
            margin: 0 0 6px 0;
            font-size: 15px;
            color: #1e40af;
        }}
        .highlight-box p {{
            margin: 0;
            font-size: 14px;
            color: #1e3a8a;
            line-height: 1.5;
        }}
        .finding-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .finding-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .badge {{
            font-size: 11px;
            font-weight: 700;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .finding-title {{
            font-weight: 700;
            font-size: 15px;
            flex-grow: 1;
        }}
        .points {{
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
        }}
        .finding-desc {{
            margin: 0;
            font-size: 14px;
            color: var(--text-muted);
            line-height: 1.4;
        }}
        .evidence {{
            margin-top: 8px;
            padding: 6px 10px;
            background: var(--bg);
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            color: #475569;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-around;
            text-align: center;
            margin-top: 8px;
        }}
        .metric-box div:first-child {{
            font-size: 24px;
            font-weight: 800;
            color: var(--primary);
        }}
        .metric-box div:last-child {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>{business.name}</h1>
                <div class="meta">{business.vertical.title()} • {business.city or ""}, {business.state or ""} {business.country or ""}</div>
                <div class="meta" style="margin-top: 6px;">Website: <a href="{business.website or '#'}" target="_blank">{business.website or 'No Website Found'}</a></div>
            </div>
            <div class="score-pill">
                <div class="score-num">{score.total_score:.0f}</div>
                <div class="score-tier">Tier {score.tier}</div>
            </div>
        </div>

        <div class="highlight-box">
            <h3>Recommended Service: {score.recommended_service}</h3>
            <p><strong>Sales Angle:</strong> {score.recommended_angle}</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Contact Information</h2>
                <div class="item"><strong>Email:</strong> {business.public_email or "None publicly found"}</div>
                <div class="item"><strong>Phone:</strong> {business.normalized_phone or business.phone or "None"}</div>
                <div class="item"><strong>Contact URL:</strong> {profile.contact_page_url if profile and profile.contact_page_url else "None"}</div>
                <div class="item"><strong>Instagram:</strong> {business.instagram or "None"}</div>
                <div class="item"><strong>Facebook:</strong> {business.facebook or "None"}</div>
                <div class="item"><strong>LinkedIn:</strong> {business.linkedin or "None"}</div>
            </div>

            <div class="card">
                <h2>Lighthouse Performance</h2>
                <div class="metric-row">
                    <div class="metric-box">
                        <div>{perf_val}</div>
                        <div>Performance</div>
                    </div>
                    <div class="metric-box">
                        <div>{seo_val}</div>
                        <div>SEO</div>
                    </div>
                    <div class="metric-box">
                        <div>{a11y_val}</div>
                        <div>A11y</div>
                    </div>
                    <div class="metric-box">
                        <div>{bp_val}</div>
                        <div>Best Pract.</div>
                    </div>
                </div>
                <div style="margin-top: 16px; font-size: 13px; color: var(--text-muted);">
                    <div><strong>LCP:</strong> {f'{lh.lcp_ms:.0f}ms' if lh and lh.lcp_ms else 'N/A'} • <strong>CLS:</strong> {lh.cls if lh and lh.cls else 'N/A'}</div>
                    <div><strong>TBT:</strong> {f'{lh.tbt_ms:.0f}ms' if lh and lh.tbt_ms else 'N/A'} • <strong>Speed Index:</strong> {f'{lh.speed_index_ms:.0f}ms' if lh and lh.speed_index_ms else 'N/A'}</div>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <h2>Key Audit Findings ({len(findings)})</h2>
            {findings_html if findings else "<p style='color:var(--text-muted); font-size:14px;'>No major technical issues identified.</p>"}
        </div>
    </div>
</body>
</html>
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return out_file
