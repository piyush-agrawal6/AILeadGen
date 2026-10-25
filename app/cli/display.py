from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.database.models import Business, Finding, LeadScore, WebsiteProfile

console = Console(legacy_windows=False)


def display_business_inspection(
    business: Business,
    score: Optional[LeadScore],
    profile: Optional[WebsiteProfile],
    findings: List[Finding],
) -> None:
    """Print a Rich terminal inspection card for a single business."""
    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold cyan", width=22)
    t.add_column("Value", style="white")

    t.add_row("Business ID", str(business.id))
    t.add_row("Name", business.name)
    t.add_row("Vertical", business.vertical.title())
    t.add_row("Location", f"{business.city or ''}, {business.state or ''} {business.country or ''}")
    t.add_row("Website", business.website or "[dim]None[/dim]")
    t.add_row("Domain", business.domain or "[dim]None[/dim]")
    t.add_row("Email", business.public_email or "[dim]None[/dim]")
    t.add_row("Phone", business.normalized_phone or business.phone or "[dim]None[/dim]")
    t.add_row("Instagram", business.instagram or "[dim]None[/dim]")
    t.add_row("Facebook", business.facebook or "[dim]None[/dim]")
    t.add_row("LinkedIn", business.linkedin or "[dim]None[/dim]")

    if score:
        t.add_row("Opportunity Score", f"[bold green]{score.total_score:.1f}[/bold green] (Tier [bold yellow]{score.tier}[/bold yellow])")
        t.add_row("Recommended Service", f"[bold yellow]{score.recommended_service}[/bold yellow]")
        t.add_row("Sales Angle", score.recommended_angle)
        t.add_row(
            "Score Breakdown",
            f"Web: {score.website_score} | SEO: {score.seo_opportunity_score} | Vert: {score.vertical_opportunity_score} | Contact: {score.contactability_score}"
        )

    if profile:
        t.add_row("HTTPS Enabled", "Yes" if profile.https_enabled else "[bold red]No[/bold red]")
        t.add_row("Mobile Viewport", "Yes" if profile.has_viewport else "[bold red]No[/bold red]")
        t.add_row("Technologies", ", ".join(profile.detected_technologies) if profile.detected_technologies else "[dim]None detected[/dim]")
        t.add_row("Analytics", ", ".join(profile.analytics_providers) if profile.analytics_providers else "[dim]No commonly detectable tag[/dim]")
        t.add_row("Schema Types", ", ".join(profile.schema_types) if profile.schema_types else "[dim]None[/dim]")

    console.print(Panel(t, title=f"[bold white]{business.name}[/bold white]", border_style="cyan"))

    if findings:
        f_table = Table(title="Audit Findings", border_style="dim")
        f_table.add_column("Severity", style="bold", width=10)
        f_table.add_column("Code", style="cyan", width=26)
        f_table.add_column("Title", style="white", width=34)
        f_table.add_column("Points", justify="right", style="green", width=8)

        for f in findings:
            sev_color = "red" if f.severity == "HIGH" else ("yellow" if f.severity == "MEDIUM" else "blue")
            f_table.add_row(
                f"[{sev_color}]{f.severity}[/{sev_color}]",
                f.finding_code,
                f.title,
                f"+{f.score_points}",
            )
        console.print(f_table)
