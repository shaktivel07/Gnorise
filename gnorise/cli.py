import typer
import json as json_lib
import sys
import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box
from typing import Optional

from gnorise.core.engine import GnoriseEngine
from gnorise.core.scorer import UsageStatus
from gnorise.core.auditor import Auditor

app = typer.Typer(
    name="gnorise",
    help="Gnorise: Understand, clean, and secure your dependencies — before they break your project.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

def print_header():
    header = Panel(
        Text.from_markup(
            "[bold blue]Gnorise[/bold blue] - Dependency Intelligence Tool\n"
            "[dim]Developed by [/dim][bold cyan]shaktivel[/bold cyan] [dim](github.com/shaktivel07)[/dim]"
        ),
        box=box.ROUNDED,
        style="blue",
        expand=False
    )
    console.print(header)

@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to the project to scan"),
    json: bool = typer.Option(False, "--json", help="Output results in JSON format"),
    ci: bool = typer.Option(False, "--ci", help="CI mode: exit with non-zero code if high-confidence unused dependencies are found"),
):
    """
    [bold green]Scan[/bold green] the project for dependencies and usage.
    """
    if not json:
        print_header()
        
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    
    if not json:
        with console.status("[bold blue]Analyzing project structure...[/bold blue]"):
            result = engine.run_scan()
    else:
        result = engine.run_scan()
    
    if json:
        output = {
            "project": result.manifest.name,
            "version": result.manifest.version,
            "developed_by": "shaktivel (github.com/shaktivel07)",
            "dependencies": {
                pkg: {
                    "status": info.status,
                    "confidence": info.confidence,
                    "usage_count": len(info.files),
                    "reason": info.reason
                } for pkg, info in result.package_usage.items()
            }
        }
        print(json_lib.dumps(output, indent=2))
    else:
        # Summary Dashboard
        total = len(result.package_usage)
        used = sum(1 for i in result.package_usage.values() if i.status == UsageStatus.USED)
        possibly = sum(1 for i in result.package_usage.values() if i.status == UsageStatus.POSSIBLY_USED)
        unused = sum(1 for i in result.package_usage.values() if i.status == UsageStatus.UNUSED)
        
        summary_panel = Panel(
            Columns([
                f"[bold white]Total:[/] {total}",
                f"[bold green]Used:[/] {used}",
                f"[bold yellow]Possibly Used:[/] {possibly}",
                f"[bold red]Unused:[/] {unused}"
            ]),
            title="[bold]Summary[/bold]",
            box=box.SIMPLE
        )
        console.print(summary_panel)
        
        table = Table(box=box.DOUBLE_EDGE)
        table.add_column("Package", style="magenta", no_wrap=True)
        table.add_column("Usage", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Status", style="bold")
        
        for pkg, info in result.package_usage.items():
            color = "green" if info.status == UsageStatus.USED else "yellow" if info.status == UsageStatus.POSSIBLY_USED else "red"
            status_styled = f"[{color}]{info.status}[/{color}]"
            table.add_row(pkg, str(len(info.files)), f"{info.confidence}%", status_styled)
        
        console.print(table)
    
    if ci:
        critical_unused = [pkg for pkg, info in result.package_usage.items() if info.status == UsageStatus.UNUSED and info.confidence > 80]
        if critical_unused:
            if not json:
                console.print(f"\n[bold red]CI Failure:[/bold red] {len(critical_unused)} high-confidence unused dependencies found.")
            sys.exit(1)

@app.command()
def doctor(
    path: str = typer.Argument(".", help="Path to the project"),
    json: bool = typer.Option(False, "--json", help="Output results in JSON format"),
):
    """
    Quick project [bold cyan]health check[/bold cyan].
    """
    if not json:
        print_header()
        
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    
    if not json:
        with console.status("[bold cyan]Running health check...[/bold cyan]"):
            result = engine.run_scan()
    else:
        result = engine.run_scan()

    unused_count = sum(1 for info in result.package_usage.values() if info.status == UsageStatus.UNUSED)
    
    if json:
        output = {
            "project": result.manifest.name,
            "health": {
                "manifest": "OK",
                "lockfile": "OK" if (root_dir / "package-lock.json").exists() else "MISSING",
                "unused_dependencies": unused_count
            }
        }
        print(json_lib.dumps(output, indent=2))
        return

    table = Table(title=f"Health Summary: {result.manifest.name or 'Unnamed'}", box=box.HORIZONTALS)
    table.add_column("Category", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Notes")
    
    table.add_row("Manifest", "[green]OK[/green]", "package.json found")
    
    lockfile_status = "[green]OK[/green]" if (root_dir / "package-lock.json").exists() else "[yellow]MISSING[/yellow]"
    table.add_row("Lockfile", lockfile_status, "package-lock.json")
    
    unused_status = "[green]Clean[/green]" if unused_count == 0 else "[yellow]Bloated[/yellow]"
    table.add_row("Dependencies", unused_status, f"{unused_count} unused packages detected")
    
    console.print(table)

@app.command()
def explain(
    package: str = typer.Argument(..., help="The package to explain"),
    path: str = typer.Option(".", help="Path to the project"),
):
    """
    [bold magenta]Explain[/bold magenta] where and why a package is used.
    """
    print_header()
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    result = engine.run_scan()
    
    if package not in result.package_usage:
        console.print(f"[red]Error: Package '{package}' not found in manifest.[/red]")
        return

    info = result.package_usage[package]
    
    console.print(Panel(f"[bold magenta]Explaining {package}[/bold magenta]", expand=False))
    console.print(f"Status: {info.status} (Confidence: {info.confidence}%)")
    
    if info.reason:
        console.print(f"Reason: [italic]{info.reason}[/italic]")
    
    if info.files:
        console.print(f"\nUsed in {len(info.files)} files:")
        for file in info.files:
            console.print(f"- {file.relative_to(root_dir)}")
            
    if info.evidence:
        console.print("\n[bold]Evidence Breakdown:[/bold]")
        for ev in info.evidence:
            console.print(f"  • [cyan]{ev.type}[/]: {ev.explanation} ([dim]{ev.weight} pts[/dim])")

@app.command()
def clean(
    path: str = typer.Option(".", help="Path to the project"),
):
    """
    Identify and [bold red]clean up[/bold red] unused dependencies.
    """
    print_header()
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    result = engine.run_scan()
    
    unused = [pkg for pkg, info in result.package_usage.items() if info.status == UsageStatus.UNUSED]
    
    if not unused:
        console.print("[green]No unused dependencies found! Your project is lean.[/green]")
        return
    
    console.print(Panel("[bold red]Unused Dependencies Found[/bold red]", expand=False))
    for pkg in unused:
        info = result.package_usage[pkg]
        console.print(f"- [yellow]{pkg}[/yellow] (Confidence: {info.confidence}%)")
    
    console.print("\n[bold]Suggested Action:[/bold] npm uninstall " + " ".join(unused))

@app.command()
def impact(
    package: str = typer.Argument(..., help="The package to analyze"),
    path: str = typer.Option(".", help="Path to the project"),
):
    """
    Analyze the [bold orange3]impact[/bold orange3] of removing a package.
    """
    print_header()
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    result = engine.run_scan()
    
    if package not in result.package_usage:
        console.print(f"[red]Error: Package '{package}' not found.[/red]")
        return

    info = result.package_usage[package]
    
    console.print(Panel(f"[bold orange3]Impact Analysis: {package}[/bold orange3]", expand=False))
    
    if info.files:
        console.print(f"[red]CODE IMPACT:[/red] Removing this will break {len(info.files)} files.")
        for file in info.files[:3]:
            console.print(f"- {file.relative_to(root_dir)}")
    else:
        console.print("[green]NO DIRECT CODE IMPACT:[/green] This package is not imported in your code.")

    dependents = [pkg for pkg, deps in result.dependency_graph.items() if package in deps]
    
    if dependents:
        console.print(f"\n[red]DEPENDENCY IMPACT:[/red] {len(dependents)} other packages depend on this.")
        for dep in dependents[:5]:
            console.print(f"- [yellow]{dep}[/yellow]")
    else:
        console.print("\n[green]NO DEPENDENCY IMPACT:[/green] No other installed packages depend on this.")

    if not info.files and not dependents:
        console.print("\n[bold green]SAFE TO REMOVE:[/bold green] This package is completely isolated.")

@app.command()
def audit(
    path: str = typer.Option(".", help="Path to the project"),
    json: bool = typer.Option(False, "--json", help="Output results in JSON format"),
    ci: bool = typer.Option(False, "--ci", help="CI mode: exit with non-zero code if used vulnerable packages are found"),
):
    """
    Context-aware [bold red]security audit[/bold red].
    """
    if not json:
        print_header()
        
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    
    if not json:
        with console.status("[bold blue]Scanning project...[/bold blue]"):
            scan_result = engine.run_scan()
    else:
        scan_result = engine.run_scan()
    
    auditor = Auditor()
    all_deps = {**scan_result.manifest.dependencies, **scan_result.manifest.dev_dependencies}
    used_packages = {pkg for pkg, info in scan_result.package_usage.items() if info.status == UsageStatus.USED}
    
    if not json:
        with console.status("[bold red]Auditing vulnerabilities...[/bold red]"):
            loop = asyncio.get_event_loop()
            audit_results = loop.run_until_complete(auditor.audit_all(all_deps, used_packages))
    else:
        loop = asyncio.get_event_loop()
        audit_results = loop.run_until_complete(auditor.audit_all(all_deps, used_packages))
    
    if json:
        output = [res.dict() for res in audit_results]
        print(json_lib.dumps(output, indent=2))
    else:
        if not audit_results:
            console.print("[green]No known vulnerabilities found in your dependencies![/green]")
        else:
            console.print(Panel("[bold red]Vulnerability Audit Results[/bold red]", expand=False))
            table = Table(box=box.SIMPLE_HEAD)
            table.add_column("Package", style="magenta")
            table.add_column("Vuln ID", style="bold")
            table.add_column("Used?", justify="center")
            table.add_column("Summary")
            
            for res in audit_results:
                used_styled = "[green]Yes[/green]" if res.is_used else "[yellow]No[/yellow]"
                for vuln in res.vulnerabilities:
                    table.add_row(res.package, vuln.id, used_styled, vuln.summary or "N/A")
            console.print(table)
            
            unused_vulns = [res for res in audit_results if not res.is_used]
            if unused_vulns:
                console.print(f"\n[cyan]Insight:[/cyan] {len(unused_vulns)} vulnerable packages are [bold]not used[/bold] in your code. You can safely remove them to reduce risk.")

    if ci:
        used_vulns = [res for res in audit_results if res.is_used]
        if used_vulns:
            if not json:
                console.print(f"\n[bold red]CI Failure:[/bold red] Found vulnerabilities in {len(used_vulns)} [bold]used[/bold] packages.")
            sys.exit(1)

if __name__ == "__main__":
    app()
