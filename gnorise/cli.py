import typer
import json as json_lib
import sys
import asyncio
import warnings
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.tree import Tree
from rich import box
from typing import Optional, Dict, List

# Suppress Tree-sitter and other FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)

from gnorise.core.engine import GnoriseEngine
from gnorise.core.scorer import UsageStatus
from gnorise.core.auditor import Auditor
from gnorise.core.awareness import get_package_description
from gnorise.core.metadata import MetadataFetcher

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
                    "status": info.status.value,
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
        used = sum(1 for i in result.package_usage.values() if i.status in [UsageStatus.USED, UsageStatus.FRAMEWORK])
        possibly = sum(1 for i in result.package_usage.values() if i.status in [UsageStatus.POSSIBLY_USED, UsageStatus.DEV_TOOL, UsageStatus.BUILD_TOOL, UsageStatus.TEST_TOOL])
        unused = sum(1 for i in result.package_usage.values() if i.status == UsageStatus.UNUSED)
        
        summary_panel = Panel(
            Columns([
                f"[bold white]Total:[/] {total}",
                f"[bold green]Used:[/] {used}",
                f"[bold yellow]Infrastructure:[/] {possibly}",
                f"[bold red]Unused:[/] {unused}"
            ]),
            title="[bold]Project Intelligence Summary[/bold]",
            box=box.SIMPLE
        )
        console.print(summary_panel)
        
        table = Table(box=box.DOUBLE_EDGE)
        table.add_column("Package", style="magenta", no_wrap=True)
        table.add_column("Usage", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Status", style="bold")
        
        for pkg, info in result.package_usage.items():
            color = "green" if info.status in [UsageStatus.USED, UsageStatus.FRAMEWORK] else "yellow" if info.status != UsageStatus.UNUSED else "red"
            status_styled = f"[{color}]{info.status.value}[/{color}]"
            table.add_row(pkg, str(len(info.files)), f"{info.confidence}%", status_styled)
        
        console.print(table)
    
    if ci:
        critical_unused = [pkg for pkg, info in result.package_usage.items() if info.status == UsageStatus.UNUSED and info.confidence > 80]
        if critical_unused:
            if not json:
                console.print(f"\n[bold red]CI Failure:[/bold red] {len(critical_unused)} high-confidence unused dependencies found.")
            sys.exit(1)

@app.command()
def why(
    package: str = typer.Argument(..., help="The package to explain"),
    path: str = typer.Option(".", help="Path to the project"),
):
    """
    [bold magenta]Why[/bold magenta] is this dependency installed?
    """
    print_header()
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    
    with console.status(f"[bold blue]Fetching live intelligence for {package}...[/bold blue]"):
        result = engine.run_scan()
        fetcher = MetadataFetcher()
        loop = asyncio.get_event_loop()
        meta = loop.run_until_complete(fetcher.fetch(package))
    
    if package not in result.package_usage:
        if package in result.dependency_graph:
            console.print(f"[yellow]Info: '{package}' is an indirect dependency (not in package.json).[/yellow]")
        else:
            console.print(f"[yellow]Info: '{package}' is not part of this project's dependency tree.[/yellow]")
            # We still proceed to show the Intelligence Report (Live Metadata)

    info = result.package_usage.get(package)
    
    console.print(Panel(f"[bold magenta]Intelligence Report: {package}[/bold magenta]", expand=False))
    
    console.print(f"[bold cyan]Description:[/] {meta.description}")
    if meta.homepage:
        console.print(f"[bold cyan]Homepage:[/] [link={meta.homepage}]{meta.homepage}[/link]")
    if meta.license:
        console.print(f"[bold cyan]License:[/] {meta.license}")
    
    if info:
        console.print(f"\nStatus: [bold]{info.status.value}[/] (Confidence: {info.confidence}%)")
        if info.reason:
            console.print(f"Primary Signal: [italic]{info.reason}[/italic]")
        
        if info.files:
            console.print(f"\n[bold]Code-level Usage:[/bold] Found in {len(info.files)} files:")
            for file in info.files[:5]:
                console.print(f"  • {file.relative_to(root_dir)}")
            if len(info.files) > 5:
                console.print(f"  [dim]... and {len(info.files) - 5} more.[/dim]")
    
    paths = engine.get_dependency_path(package, result.dependency_graph)
    if paths:
        console.print(f"\n[bold]Dependency Chain:[/bold]")
        for p in paths:
            console.print(f"  • {' → '.join(p)}")

@app.command()
def trace(
    package: str = typer.Argument(..., help="The package to trace"),
    path: str = typer.Option(".", help="Path to the project"),
):
    """
    [bold cyan]Trace[/bold cyan] the dependency chain from root to package.
    """
    print_header()
    root_dir = Path(path)
    engine = GnoriseEngine(root_dir)
    result = engine.run_scan()
    
    paths = engine.get_dependency_path(package, result.dependency_graph)
    
    if not paths:
        console.print(f"[red]Error: Could not find dependency chain for '{package}'.[/red]")
        return
        
    console.print(Panel(f"[bold cyan]Dependency Trace: {package}[/bold cyan]", expand=False))
    
    for i, p in enumerate(paths):
        tree = Tree(f"[bold green]{p[0]}[/]")
        current_node = tree
        for part in p[1:]:
            current_node = current_node.add(f"[cyan]{part}[/]")
        console.print(tree)
        if i < len(paths) - 1:
            console.print("[dim]OR[/dim]")

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
    console.print("[dim]Note: Verify if these are used in build tools or external scripts before removal.[/dim]")

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
    
    with console.status(f"[bold blue]Fetching metadata for {package}...[/bold blue]"):
        result = engine.run_scan()
        fetcher = MetadataFetcher()
        loop = asyncio.get_event_loop()
        meta = loop.run_until_complete(fetcher.fetch(package))
    
    if package not in result.package_usage:
        console.print(f"[red]Error: Package '{package}' not found.[/red]")
        return

    info = result.package_usage[package]
    
    console.print(Panel(f"[bold orange3]Impact Analysis: {package}[/bold orange3]", expand=False))
    
    console.print(f"[bold cyan]Package Description:[/] {meta.description}")

    # 1. Direct code usage
    if info.files:
        console.print(f"[red]CODE IMPACT:[/red] Removing this will break {len(info.files)} files.")
        for file in info.files[:3]:
            console.print(f"- {file.relative_to(root_dir)}")
    else:
        console.print("[yellow]NO DIRECT CODE USAGE DETECTED[/yellow]")
        if info.status in [UsageStatus.DEV_TOOL, UsageStatus.BUILD_TOOL, UsageStatus.TEST_TOOL]:
            console.print(f"\n[bold yellow]Caution:[/bold yellow] This is a development/build tool.")
            console.print("Removing it may break your build pipeline or IDE tooling.")
            console.print("[bold green]Recommendation:[/bold green] Keep unless you are certain it is no longer needed.")

    # 2. Dependency graph impact
    dependents = [pkg for pkg, deps in result.dependency_graph.items() if package in deps]
    
    if dependents:
        console.print(f"\n[red]DEPENDENCY IMPACT:[/red] {len(dependents)} other packages depend on this.")
        for dep in dependents[:5]:
            console.print(f"- [yellow]{dep}[/yellow]")
    else:
        console.print("\n[green]NO DEPENDENCY IMPACT:[/green] No other installed packages depend on this.")

    if not info.files and not dependents and info.status == UsageStatus.UNUSED:
        console.print("\n[bold green]Likely safe to remove[/bold green], but verify build scripts first.")

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
    used_packages = {pkg for pkg, info in scan_result.package_usage.items() if info.status in [UsageStatus.USED, UsageStatus.FRAMEWORK]}
    
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
            console.print(Panel("[bold red]Security Audit Summary[/bold red]", expand=False))
            
            table = Table(box=box.SIMPLE_HEAD)
            table.add_column("Package", style="magenta")
            table.add_column("Vulnerabilities", justify="center")
            table.add_column("Used?", justify="center")
            table.add_column("Recommended Action")
            
            for res in audit_results:
                used_styled = "[green]Yes[/green]" if res.is_used else "[yellow]No[/yellow]"
                vuln_count = len(res.vulnerabilities)
                
                action = "Upgrade to latest" if res.is_used else "Safe to remove"
                table.add_row(res.package, str(vuln_count), used_styled, action)
            
            console.print(table)
            
            # Specific insights
            unused_vulns = [res for res in audit_results if not res.is_used]
            if unused_vulns:
                console.print(f"\n[cyan]Insight:[/cyan] {len(unused_vulns)} vulnerable packages are [bold]not used[/bold] in your code. Removing them is the safest fix.")

    if ci:
        used_vulns = [res for res in audit_results if res.is_used]
        if used_vulns:
            if not json:
                console.print(f"\n[bold red]CI Failure:[/bold red] Found vulnerabilities in {len(used_vulns)} [bold]used[/bold] packages.")
            sys.exit(1)

if __name__ == "__main__":
    app()
