import click
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .init import run_init
from .agent import Agent
from . import tools

console = Console()

def load_config():
    """Load the user configuration from the standard home directory path."""
    config_path = Path.home() / ".config" / "atomic-vault" / "config.yaml"
    if not config_path.exists():
        return None
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """Atomic Vault - LLM-Managed Knowledge Base."""
    pass

@cli.command()
def init():
    """Initialize a new vault and configure the LLM Architect."""
    run_init()

@cli.command()
@click.argument("filename", required=False)
def ingest(filename):
    """Process files from /Raw into atomic knowledge units."""
    config = load_config()
    if not config:
        console.print("[red]Error: Vault not initialized. Run 'av init' first.[/red]")
        return
    
    vault_root = config["vault_root"]
    agent = Agent(config)
    
    files = [filename] if filename else tools.list_raw_files(vault_root)
    if not files:
        console.print("[yellow]No new files found in /Raw to ingest.[/yellow]")
        return

    console.print(f"[bold blue]Processing {len(files)} file(s)...[/bold blue]")
    total_notes = 0
    
    for f in files:
        try:
            with console.status(f"[blue]Architect is processing {f}..."):
                count = agent.ingest(f)
                tools.archive_raw_file(vault_root, f)
                console.print(f"[green]✓ {f}: {count} note(s) mirrored to vault.[/green]")
                total_notes += count
        except Exception as e:
            console.print(f"[red]✗ Failed to process {f}: {e}[/red]")

    if total_notes > 0:
        console.print(f"\n[bold green]Success: {total_notes} notes created in total.[/bold green]")

@cli.command()
def sync():
    """Re-index the entire vault from the filesystem to the vector DB."""
    config = load_config()
    if not config:
        return
    
    agent = Agent(config)
    vault_root = Path(config["vault_root"])
    notes_path = vault_root / "Atomic Notes"
    
    if "notes" in agent.rag.db.table_names():
        agent.rag.db.drop_table("notes")
    
    console.print("[bold blue]Syncing filesystem to Vector DB...[/bold blue]")
    count = 0
    for note_file in notes_path.rglob("*.md"):
        if note_file.is_file():
            content = note_file.read_text(encoding="utf-8")
            meta = tools.find_metadata(content)
            vector = agent._embed(content[:2000])
            # Use relative path from vault root as the file_path ID
            rel_p = f"/{note_file.relative_to(vault_root)}"
            agent.rag.upsert_note(meta["title"], meta["domain"], content, vector, rel_p)
            count += 1
            
    console.print(f"[green]✓ Successfully re-indexed {count} notes.[/green]")

@cli.command()
@click.option("--fix", is_flag=True, help="Auto-remediate issues using the LLM Architect.")
@click.option("--verbose", "-v", is_flag=True, help="Show full architect's reasoning.")
def lint(fix, verbose):
    """Perform a vault health check and link audit."""
    config = load_config()
    if not config:
        return
    
    agent = Agent(config)
    with console.status("[bold blue]Auditing vault health..."):
        report = agent.lint(fix=fix)
        
        if fix:
            console.print("\n[bold green]Remediation complete:[/bold green]")
            for action in report["actions"]:
                console.print(f" [green]✓[/green] {action['file_path']}: Updated")
        else:
            console.print(f"\n[bold cyan]Architect's Summary:[/bold cyan] {report['summary']}")
            
            if report["actions"]:
                table = Table(title="Vault Actions Recommended")
                table.add_column("File", style="yellow")
                table.add_column("Type", style="cyan")
                
                for action in report["actions"]:
                    action_type = "Delete" if action["is_deletion"] else "Update/Create"
                    table.add_row(action["file_path"], action_type)
                console.print(table)
            else:
                console.print("[green]No issues found. Vault is healthy.[/green]")

        if verbose:
            console.print("\n[bold]Full Response:[/bold]")
            console.print(report["raw"])

@cli.command()
def status():
    """Display vault metrics and domain distribution."""
    config = load_config()
    if not config:
        return
    
    agent = Agent(config)
    stats = agent.rag.get_vault_stats()
    
    table = Table(title="Atomic Vault Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Notes", str(stats["total_notes"]))
    for domain, count in stats["by_domain"].items():
        table.add_row(f"Domain: {domain}", str(count))
        
    console.print(table)

if __name__ == "__main__":
    cli()
