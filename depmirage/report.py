"""Rendering of scan results with rich, plus exit-code logic.

A "finding" is anything that should fail a CI gate: a hallucinated package, a
typosquat/lookalike, or a hardcoded secret. "Could not verify" is a warning,
not a finding, so a flaky network does not fail the build on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from . import registry
from .secrets import Finding as SecretFinding


@dataclass
class DepResult:
    name: str
    source: str            # which requirements file it came from
    existence: str          # registry.EXISTS / MISSING / UNKNOWN
    lookalike: str = ""     # nearest popular name, if any

    @property
    def is_finding(self) -> bool:
        return self.existence == registry.MISSING or bool(self.lookalike)


@dataclass
class ScanReport:
    deps: List[DepResult] = field(default_factory=list)
    secrets: List[SecretFinding] = field(default_factory=list)

    @property
    def finding_count(self) -> int:
        return sum(1 for d in self.deps if d.is_finding) + len(self.secrets)

    @property
    def exit_code(self) -> int:
        return 1 if self.finding_count > 0 else 0


def render(report: ScanReport, console=None, offline: bool = False) -> None:
    """Print the report as colored rich tables."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = console or Console()

    mode = "[dim](offline mode)[/dim]" if offline else ""
    console.print(f"[bold]depmirage[/bold] dependency & secret scan {mode}\n")

    # --- Dependencies table ---
    if report.deps:
        table = Table(title="Dependencies", box=box.ROUNDED, show_lines=False)
        table.add_column("Package", style="bold")
        table.add_column("Status", no_wrap=True)
        table.add_column("Detail")
        for d in report.deps:
            status, detail = _dep_status(d)
            table.add_row(d.name, status, detail)
        console.print(table)
    else:
        console.print("[dim]No dependencies found to check.[/dim]")

    # --- Secrets table ---
    if report.secrets:
        stable = Table(title="Hardcoded secrets", box=box.ROUNDED)
        stable.add_column("File")
        stable.add_column("Line", justify="right")
        stable.add_column("Type")
        stable.add_column("Value (masked)")
        for s in report.secrets:
            stable.add_row(
                s.file, str(s.line), s.kind, f"[red]{s.masked}[/red]"
            )
        console.print(stable)
    else:
        console.print("[dim]No hardcoded secrets detected.[/dim]")

    # --- Summary ---
    n = report.finding_count
    console.print()
    if n == 0:
        console.print("[bold green][PASS][/bold green] No findings. Exit code 0.")
    else:
        console.print(
            f"[bold red][FAIL][/bold red] {n} finding(s). Exit code 1."
        )
    console.print()


def _dep_status(d: DepResult):
    """Return (status_cell, detail_cell) markup for a dependency row."""
    if d.lookalike and d.existence == registry.MISSING:
        return (
            "[bold red][FAIL][/bold red]",
            f"hallucinated / slopsquatting risk; "
            f"lookalike of [bold]{d.lookalike}[/bold] (high typosquat risk)",
        )
    if d.existence == registry.MISSING:
        return (
            "[bold red][FAIL][/bold red]",
            "does not exist - hallucinated / slopsquatting risk",
        )
    if d.lookalike:
        return (
            "[bold red][FAIL][/bold red]",
            f"lookalike of [bold]{d.lookalike}[/bold] - high typosquat risk",
        )
    if d.existence == registry.EXISTS:
        return ("[bold green][PASS][/bold green]", "exists on PyPI")
    # UNKNOWN
    return ("[yellow][WARN][/yellow]", "could not verify (network/registry)")


def to_dict(report: ScanReport, offline: bool = False) -> dict:
    """Serialize the report for --json output."""
    return {
        "offline": offline,
        "finding_count": report.finding_count,
        "exit_code": report.exit_code,
        "dependencies": [
            {
                "name": d.name,
                "source": d.source,
                "existence": d.existence,
                "lookalike": d.lookalike or None,
                "is_finding": d.is_finding,
            }
            for d in report.deps
        ],
        "secrets": [
            {
                "file": s.file,
                "line": s.line,
                "type": s.kind,
                "masked": s.masked,
            }
            for s in report.secrets
        ],
    }
