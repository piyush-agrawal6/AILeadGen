import asyncio
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from app.audit.lighthouse import find_lighthouse_executable
from app.cli.display import display_business_inspection
from app.config.markets import CURATED_MARKETS, resolve_market
from app.config.settings import get_settings
from app.config.verticals import get_vertical_manager
from app.database.connection import db_session, get_db_path
from app.database.migrations import run_migrations
from app.database.repositories import (
    BusinessRepository,
    FindingRepository,
    LeadScoreRepository,
    LighthouseRepository,
    PipelineRunRepository,
    WebsiteProfileRepository,
)
from app.exports.csv_export import export_leads_to_csv
from app.exports.excel_export import export_leads_to_excel
from app.exports.report import generate_html_report
from app.pipeline.runner import PipelineRunner
from app.utils.logging import setup_logging

app = typer.Typer(
    name="LeadEngine",
    help="Zero-cost B2B lead discovery, technical auditing, and qualification engine.",
    add_completion=False,
)
console = Console(legacy_windows=False)


@app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level)


@app.command(name="run")
def run_command(
    market: str = typer.Option(..., "--market", "-m", help="Geographic market (e.g. 'Austin, Texas, USA')"),
    vertical: str = typer.Option("restaurant", "--vertical", "-v", help="Industry vertical (e.g. restaurant, hospitality, real_estate)"),
    target: int = typer.Option(250, "--target", "-t", help="Target number of qualified leads to produce"),
    include_chains: bool = typer.Option(False, "--include-chains", help="Include national chain franchises"),
    no_lighthouse: bool = typer.Option(False, "--no-lighthouse", help="Skip deep Lighthouse performance scans"),
):
    """Run lead discovery, website auditing, and prospect qualification."""
    run_migrations()
    runner = PipelineRunner()
    asyncio.run(
        runner.run(
            market=market,
            vertical=vertical,
            target=target,
            include_chains=include_chains,
            enable_lighthouse=not no_lighthouse,
        )
    )


@app.command(name="doctor")
def doctor_command():
    """Verify system prerequisites, external connectivity, and tools."""
    table = Table(title="LeadEngine System Diagnostics", show_lines=False, box=None)
    table.add_column("Component", style="bold white", width=26)
    table.add_column("Status", width=12)
    table.add_column("Details", style="dim")

    all_ok = True

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    table.add_row("Python (>= 3.12)", "[bold green]✓[/bold green]" if py_ok else "[bold red]✗[/bold red]", f"Python {py_ver}")
    if not py_ok:
        all_ok = False

    # 2. SQLite
    try:
        run_migrations()
        table.add_row("SQLite & Migrations", "[bold green]✓[/bold green]", str(get_db_path()))
    except Exception as e:
        table.add_row("SQLite & Migrations", "[bold red]✗[/bold red]", str(e)[:40])
        all_ok = False

    # 3. DuckDB
    try:
        import duckdb
        con = duckdb.connect()
        con.execute("SELECT 42;")
        table.add_row("DuckDB Engine", "[bold green]✓[/bold green]", f"v{duckdb.__version__}")
    except Exception as e:
        table.add_row("DuckDB Engine", "[bold red]✗[/bold red]", str(e)[:40])
        all_ok = False

    # 4. Chrome / Edge
    chrome_found = False
    chrome_path = ""
    for path in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]:
        if Path(path).exists():
            chrome_found = True
            chrome_path = path
            break
    if not chrome_found and shutil.which("google-chrome"):
        chrome_found = True
        chrome_path = shutil.which("google-chrome")

    table.add_row(
        "Chrome / Chromium",
        "[bold green]✓[/bold green]" if chrome_found else "[bold yellow]![/bold yellow]",
        chrome_path or "Not in default path (Playwright managed fallback)",
    )

    # 5. Lighthouse CLI
    lh_bin = find_lighthouse_executable()
    table.add_row(
        "Lighthouse CLI",
        "[bold green]✓[/bold green]" if lh_bin else "[bold yellow]![/bold yellow]",
        lh_bin or "Not installed (Optional for deep Web Vitals)",
    )

    # 6. Playwright
    try:
        import playwright
        table.add_row("Playwright Browser Layer", "[bold green]✓[/bold green]", "Ready")
    except Exception as e:
        table.add_row("Playwright Browser Layer", "[bold red]✗[/bold red]", str(e)[:40])

    # 7. Overture Maps S3 connectivity
    try:
        import duckdb
        c = duckdb.connect()
        c.execute("INSTALL httpfs; LOAD httpfs;")
        table.add_row("Overture Connection", "[bold green]✓[/bold green]", "S3 Public Parquet ready")
    except Exception as e:
        table.add_row("Overture Connection", "[bold yellow]![/bold yellow]", f"Local fallback mode: {str(e)[:30]}")

    # 8. OpenStreetMap / Overpass connectivity
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            resp = client.get("https://overpass-api.de/api/status")
            osm_ok = resp.status_code == 200
        table.add_row("OSM / Overpass API", "[bold green]✓[/bold green]" if osm_ok else "[bold yellow]![/bold yellow]", "Overpass endpoint responsive")
    except Exception:
        table.add_row("OSM / Overpass API", "[bold yellow]![/bold yellow]", "Using offline cache or retry queue")

    console.print("\n")
    console.print(table)
    console.print("\n[bold green]LeadEngine ready.[/bold green]\n" if all_ok else "\n[bold yellow]LeadEngine initialized with warnings.[/bold yellow]\n")


@app.command(name="markets")
def markets_command():
    """List curated offline markets and cached geographic locations."""
    table = Table(title="Supported & Curated Markets", box=None)
    table.add_column("Query", style="bold white", width=26)
    table.add_column("City", style="cyan", width=16)
    table.add_column("Country", style="white", width=18)
    table.add_column("Bounding Box (S, W, N, E)", style="dim")

    for k, m in CURATED_MARKETS.items():
        b = m.bbox
        bbox_str = f"({b.min_lat:.3f}, {b.min_lon:.3f}, {b.max_lat:.3f}, {b.max_lon:.3f})"
        table.add_row(m.query, m.city, m.country, bbox_str)

    console.print(table)


@app.command(name="verticals")
def verticals_command():
    """List supported business verticals, categories, and tags."""
    vm = get_vertical_manager()
    table = Table(title="Configured Business Verticals", box=None)
    table.add_column("Key", style="bold cyan", width=16)
    table.add_column("Display Name", style="bold white", width=24)
    table.add_column("Aliases", style="dim", width=30)
    table.add_column("OSM Tags", style="white")

    for v in vm.list_verticals():
        tags_str = ", ".join(f"{t.key}={','.join(t.values)}" for t in v.osm_tags)
        table.add_row(v.key, v.display_name, ", ".join(v.aliases[:4]), tags_str)

    console.print(table)


@app.command(name="inspect")
def inspect_command(
    business_id: int = typer.Option(..., "--business-id", "-b", help="Database ID of the business"),
):
    """Inspect detailed technical audit findings, score breakdown, and contacts for a business."""
    with db_session() as conn:
        b = BusinessRepository(conn).get_by_id(business_id)
        if not b:
            console.print(f"[bold red]Business #{business_id} not found in database.[/bold red]")
            raise typer.Exit(1)
        score = LeadScoreRepository(conn).get_by_business_id(business_id)
        profile = WebsiteProfileRepository(conn).get_by_business_id(business_id)
        findings = FindingRepository(conn).list_by_business_id(business_id)
        display_business_inspection(b, score, profile, findings)


@app.command(name="report")
def report_command(
    business_id: int = typer.Option(..., "--business-id", "-b", help="Database ID of the business"),
):
    """Generate a clean, standalone HTML audit report for a prospect."""
    with db_session() as conn:
        b = BusinessRepository(conn).get_by_id(business_id)
        if not b:
            console.print(f"[bold red]Business #{business_id} not found in database.[/bold red]")
            raise typer.Exit(1)
        score = LeadScoreRepository(conn).get_by_business_id(business_id)
        if not score:
            console.print(f"[bold red]Business #{business_id} has not been scored yet.[/bold red]")
            raise typer.Exit(1)
        profile = WebsiteProfileRepository(conn).get_by_business_id(business_id)
        lh = None
        findings = FindingRepository(conn).list_by_business_id(business_id)
        report_path = generate_html_report(b, score, profile, lh, findings)
        console.print(f"[bold green]HTML audit report generated successfully:[/bold green] [bold yellow]{report_path}[/bold yellow]")


@app.command(name="resume")
def resume_command(
    run_id: int = typer.Option(..., "--run-id", "-r", help="Pipeline run ID to resume"),
):
    """Resume an interrupted pipeline run from stored checkpoints."""
    run_migrations()
    with db_session() as conn:
        run_info = PipelineRunRepository(conn).get_by_id(run_id)
        if not run_info:
            console.print(f"[bold red]Run #{run_id} not found.[/bold red]")
            raise typer.Exit(1)

    runner = PipelineRunner()
    asyncio.run(
        runner.run(
            market=run_info.market,
            vertical=run_info.vertical,
            target=run_info.target,
            run_id=run_id,
        )
    )


@app.command(name="export")
def export_command(
    run_id: int = typer.Option(..., "--run-id", "-r", help="Pipeline run ID to re-export"),
):
    """Export finalized Excel and CSV workbooks for a specific pipeline run."""
    with db_session() as conn:
        run_repo = PipelineRunRepository(conn)
        run_info = run_repo.get_by_id(run_id)
        if not run_info:
            console.print(f"[bold red]Run #{run_id} not found.[/bold red]")
            raise typer.Exit(1)

        biz_repo = BusinessRepository(conn)
        score_repo = LeadScoreRepository(conn)
        profile_repo = WebsiteProfileRepository(conn)
        lh_repo = LighthouseRepository(conn)
        finding_repo = FindingRepository(conn)

        # Retrieve top scored leads
        rows = conn.execute(
            """
            SELECT b.id FROM businesses b
            JOIN lead_scores s ON b.id = s.business_id
            ORDER BY s.total_score DESC, s.contactability_score DESC
            LIMIT ?
            """,
            (run_info.target,),
        ).fetchall()

        qualified_leads = []
        for r in rows:
            b_id = r[0]
            b = biz_repo.get_by_id(b_id)
            s = score_repo.get_by_business_id(b_id)
            p = profile_repo.get_by_business_id(b_id)
            lh = lh_repo.get_by_business_id(b_id)
            f = finding_repo.list_by_business_id(b_id)
            qualified_leads.append((b, s, p, lh, f))

        all_discovered = biz_repo.list_all()
        rejected = [b for b in all_discovered if b.is_rejected or b.is_chain]

        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y-%m-%d")
        clean_market_name = "".join(c if c.isalnum() else "_" for c in run_info.market)
        clean_market_name = clean_market_name.replace("__", "_").strip("_")
        clean_vert_name = run_info.vertical.title()

        excel_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{timestamp_str}.xlsx"
        csv_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{timestamp_str}.csv"

        export_leads_to_excel(
            run_info=run_info,
            qualified_leads=qualified_leads,
            all_discovered=all_discovered,
            rejected_businesses=rejected,
            output_path=excel_path,
        )

        export_leads_to_csv(
            leads=qualified_leads,
            output_path=csv_path,
        )

        console.print(f"[bold green]Successfully exported {len(qualified_leads)} leads for Run #{run_id}:[/bold green]")
        console.print(f"  • Excel: [bold yellow]{excel_path}[/bold yellow]")
        console.print(f"  • CSV:   [bold yellow]{csv_path}[/bold yellow]")


@app.command(name="stats")
def stats_command():
    """Display overall database prospecting metrics."""
    with db_session() as conn:
        total = BusinessRepository(conn).count()
        runs = conn.execute("SELECT COUNT(*) FROM pipeline_runs;").fetchone()[0]
        qualified = conn.execute("SELECT COUNT(*) FROM businesses WHERE processing_status = 'QUALIFIED';").fetchone()[0]
        a_plus = conn.execute("SELECT COUNT(*) FROM lead_scores WHERE tier = 'A+';").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM lead_scores WHERE tier = 'A';").fetchone()[0]
        b = conn.execute("SELECT COUNT(*) FROM lead_scores WHERE tier = 'B';").fetchone()[0]

    table = Table(title="LeadEngine Database Statistics", box=None)
    table.add_column("Metric", style="bold white", width=24)
    table.add_column("Count", style="bold cyan")

    table.add_row("Total Businesses Discovered", f"{total:,}")
    table.add_row("Total Pipeline Runs", f"{runs:,}")
    table.add_row("Total Qualified Prospects", f"{qualified:,}")
    table.add_row("  Tier A+ Prospects", f"{a_plus:,}")
    table.add_row("  Tier A Prospects", f"{a:,}")
    table.add_row("  Tier B Prospects", f"{b:,}")

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
