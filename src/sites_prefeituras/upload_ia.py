"""Upload utilities for Internet Archive.

This module handles uploading data to Internet Archive including:
- Dashboard JSON files
- Quarantine lists
- PSI audit results (via legacy upload_to_ia.py)
"""

import os
from datetime import datetime
from pathlib import Path

import typer
from internetarchive import upload
from rich.console import Console

console = Console()


def upload_dashboard_json(
    dashboard_dir: str,
    item_identifier: str,
    access_key: str,
    secret_key: str,
) -> bool:
    """Upload dashboard JSON files to Internet Archive.

    Args:
        dashboard_dir: Directory containing dashboard JSON files
        item_identifier: Internet Archive item identifier
        access_key: IA access key
        secret_key: IA secret key

    Returns:
        True if successful, False otherwise
    """
    try:
        # Find all JSON files in dashboard directory
        json_files = {}
        dashboard_path = Path(dashboard_dir)

        if not dashboard_path.exists():
            console.print(f"[yellow]Warning: Dashboard directory not found: {dashboard_dir}[/yellow]")
            return False

        for json_file in dashboard_path.glob("*.json"):
            name = json_file.name
            json_files[name] = str(json_file)

        if not json_files:
            console.print(f"[yellow]Warning: No JSON files found in {dashboard_dir}[/yellow]")
            return False

        # Prepare metadata
        upload_date = datetime.utcnow().strftime("%Y-%m-%d")
        metadata = {
            "title": f"PSI Dashboard Data ({upload_date})",
            "description": "Dados JSON estaticos para dashboard de auditoria de sites de prefeituras brasileiras",
            "mediatype": "data",
            "collection": "opensource_data",
            "date": datetime.utcnow().isoformat(),
        }

        # Upload to Internet Archive
        console.print(f"[blue]Uploading {len(json_files)} dashboard JSON files to Internet Archive...[/blue]")
        upload(
            identifier=item_identifier,
            files=json_files,
            metadata=metadata,
            access_key=access_key,
            secret_key=secret_key,
            verbose=True,
        )

        console.print(f"[green]Successfully uploaded dashboard files: {list(json_files.keys())}[/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error uploading dashboard JSON to Internet Archive: {e}[/red]")
        return False


def upload_quarantine(
    quarantine_files: list[str],
    item_identifier: str,
    access_key: str,
    secret_key: str,
) -> bool:
    """Upload quarantine lists to Internet Archive.

    Args:
        quarantine_files: List of quarantine file paths to upload
        item_identifier: Internet Archive item identifier
        access_key: IA access key
        secret_key: IA secret key

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build files dictionary for upload
        files_to_upload = {}
        for file_path in quarantine_files:
            path = Path(file_path)
            if not path.exists():
                console.print(f"[yellow]Warning: Quarantine file not found: {file_path}[/yellow]")
                continue
            files_to_upload[path.name] = str(path)

        if not files_to_upload:
            console.print("[yellow]Warning: No quarantine files to upload[/yellow]")
            return False

        # Prepare metadata
        upload_date = datetime.utcnow().strftime("%Y-%m-%d")
        metadata = {
            "title": f"PSI Quarantine List ({upload_date})",
            "description": "Sites com falhas persistentes que precisam investigacao - PageSpeed Insights audits",
            "mediatype": "data",
            "collection": "opensource_data",
            "date": datetime.utcnow().isoformat(),
        }

        # Upload to Internet Archive
        console.print(f"[blue]Uploading {len(files_to_upload)} quarantine files to Internet Archive...[/blue]")
        upload(
            identifier=item_identifier,
            files=files_to_upload,
            metadata=metadata,
            access_key=access_key,
            secret_key=secret_key,
            verbose=True,
        )

        console.print(f"[green]Successfully uploaded quarantine files: {list(files_to_upload.keys())}[/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error uploading quarantine to Internet Archive: {e}[/red]")
        return False


# CLI interface
cli = typer.Typer(
    name="upload-ia",
    help="Upload data to Internet Archive",
)


@cli.command(name="dashboard")
def upload_dashboard_cmd(
    dashboard_dir: str = typer.Argument(..., help="Directory containing dashboard JSON files"),
    item_identifier: str = typer.Option(..., "--item", help="Internet Archive item identifier"),
    access_key: str | None = typer.Option(None, "--access-key", help="IA access key (or set IA_ACCESS_KEY env var)"),
    secret_key: str | None = typer.Option(None, "--secret-key", help="IA secret key (or set IA_SECRET_KEY env var)"),
) -> None:
    """Upload dashboard JSON files to Internet Archive."""
    # Get credentials from environment if not provided
    access_key = access_key or os.getenv("IA_ACCESS_KEY")
    secret_key = secret_key or os.getenv("IA_SECRET_KEY")

    if not access_key or not secret_key:
        console.print("[red]Error: IA_ACCESS_KEY and IA_SECRET_KEY must be provided[/red]")
        raise typer.Exit(1)

    success = upload_dashboard_json(
        dashboard_dir=dashboard_dir,
        item_identifier=item_identifier,
        access_key=access_key,
        secret_key=secret_key,
    )

    if not success:
        raise typer.Exit(1)


@cli.command(name="quarantine")
def upload_quarantine_cmd(
    quarantine_files: list[str] = typer.Argument(..., help="Quarantine files to upload"),
    item_identifier: str = typer.Option(..., "--item", help="Internet Archive item identifier"),
    access_key: str | None = typer.Option(None, "--access-key", help="IA access key (or set IA_ACCESS_KEY env var)"),
    secret_key: str | None = typer.Option(None, "--secret-key", help="IA secret key (or set IA_SECRET_KEY env var)"),
) -> None:
    """Upload quarantine lists to Internet Archive."""
    # Get credentials from environment if not provided
    access_key = access_key or os.getenv("IA_ACCESS_KEY")
    secret_key = secret_key or os.getenv("IA_SECRET_KEY")

    if not access_key or not secret_key:
        console.print("[red]Error: IA_ACCESS_KEY and IA_SECRET_KEY must be provided[/red]")
        raise typer.Exit(1)

    success = upload_quarantine(
        quarantine_files=quarantine_files,
        item_identifier=item_identifier,
        access_key=access_key,
        secret_key=secret_key,
    )

    if not success:
        raise typer.Exit(1)


if __name__ == "__main__":
    cli()
