from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(legacy_windows=False)


class PipelineDisplay:
    @staticmethod
    def print_stage_start(stage_num: int, total_stages: int, title: str) -> None:
        console.print(f"\n[bold cyan][{stage_num}/{total_stages}][/bold cyan] [bold white]{title}[/bold white]")

    @staticmethod
    def print_stage_success(message: str) -> None:
        console.print(f"  [bold green]✓[/bold green] {message}")

    @staticmethod
    def print_stage_info(message: str) -> None:
        console.print(f"    [dim]•[/dim] {message}")

    @staticmethod
    def print_stage_warning(message: str) -> None:
        console.print(f"  [bold yellow]![/bold yellow] {message}")

    @staticmethod
    def print_stage_error(message: str) -> None:
        console.print(f"  [bold red]✗[/bold red] {message}")

    @staticmethod
    def print_run_summary(
        market: str,
        vertical: str,
        target: int,
        raw_found: int,
        deduped: int,
        filtered: int,
        websites: int,
        no_websites: int,
        audited: int,
        qualified: int,
        a_plus: int,
        a: int,
        b: int,
        exported: int,
        output_xlsx: str,
        output_csv: str,
        runtime_sec: float,
    ) -> None:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="bold white")
        table.add_column("Value", style="cyan")

        table.add_row("Market", market)
        table.add_row("Vertical", vertical)
        table.add_row("Requested Target", str(target))
        table.add_row("Raw Discovered", f"{raw_found:,}")
        table.add_row("After Dedupe", f"{deduped:,}")
        table.add_row("Valid Candidates", f"{filtered:,}")
        table.add_row("Reachable Websites", f"{websites:,}")
        table.add_row("No Website Opportunities", f"{no_websites:,}")
        table.add_row("Sites Audited", f"{audited:,}")
        table.add_row("Qualified Prospects", f"{qualified:,}")
        table.add_row("  Tier A+ (Hot)", f"{a_plus:,}")
        table.add_row("  Tier A", f"{a:,}")
        table.add_row("  Tier B", f"{b:,}")
        table.add_row("Exported Leads", f"[bold green]{exported:,}[/bold green]")
        table.add_row("Execution Time", f"{runtime_sec:.1f}s")
        table.add_row("Excel Output", f"[bold yellow]{output_xlsx}[/bold yellow]")
        table.add_row("CSV Output", f"[bold yellow]{output_csv}[/bold yellow]")

        console.print("\n")
        console.print(
            Panel(
                table,
                title="[bold green]LEADENGINE RUN COMPLETE[/bold green]",
                subtitle="[dim]Zero-cost Prospecting Engine[/dim]",
                border_style="green",
            )
        )
