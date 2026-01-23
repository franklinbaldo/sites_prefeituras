"""Interface de linha de comando para Sites Prefeituras."""

import asyncio
import os
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from .collector import BatchProcessor, audit_single_site
from .models import BatchAuditConfig, SiteAudit
from .storage import DuckDBStorage

app = typer.Typer(
    name="sites-prefeituras",
    help="Auditoria automatizada de sites de prefeituras brasileiras",
    rich_markup_mode="rich",
)
console = Console()


def get_api_key() -> str:
    """Obtém chave da API do PageSpeed Insights."""
    # Aceita ambos os nomes para compatibilidade com GitHub Actions
    api_key = os.getenv("PAGESPEED_API_KEY") or os.getenv("PSI_KEY")
    if not api_key:
        console.print("[red]PAGESPEED_API_KEY ou PSI_KEY nao configurada![/red]")
        console.print(
            "Configure com: [bold]export PAGESPEED_API_KEY='sua_chave'[/bold]"
        )
        raise typer.Exit(1)
    return api_key


@app.command()
def audit(
    url: str = typer.Argument(..., help="URL do site para auditar"),
    output: str = typer.Option("console", help="Formato de saída: console, json"),
    save_to_db: bool = typer.Option(True, help="Salvar resultado no banco"),
) -> None:
    """Executa auditoria de um site específico."""
    api_key = get_api_key()

    console.print(f"🔍 Auditando: [bold blue]{url}[/bold blue]")

    async def run_audit() -> None:
        result = await audit_single_site(url, api_key)

        if save_to_db:
            storage = DuckDBStorage()
            await storage.initialize()
            audit_id = await storage.save_audit(result)
            await storage.close()
            console.print(f"💾 Salvo no banco com ID: {audit_id}")

        if output == "console":
            _display_audit_result(result)
        elif output == "json":
            console.print(JSON(result.model_dump_json()))

    asyncio.run(run_audit())


@app.command()
def batch(
    csv_file: str = typer.Argument(..., help="Arquivo CSV com URLs"),
    output_dir: str = typer.Option("./output", help="Diretorio de saida"),
    max_concurrent: int = typer.Option(10, help="Maximo de requisicoes simultaneas"),
    requests_per_second: float = typer.Option(
        3.5, help="Taxa de requisicoes por segundo (max 4.0)"
    ),
    url_column: str = typer.Option("url", help="Nome da coluna com URLs"),
    skip_recent_hours: int = typer.Option(
        24,
        "--skip-recent",
        help="Pular sites auditados nas ultimas N horas (0=desativado)",
    ),
    export_parquet: bool = typer.Option(True, help="Exportar para Parquet"),
    export_json: bool = typer.Option(True, help="Exportar para JSON"),
) -> None:
    """Executa auditoria em lote a partir de arquivo CSV."""
    api_key = get_api_key()

    if not Path(csv_file).exists():
        console.print(f"[red]Arquivo nao encontrado: {csv_file}[/red]")
        raise typer.Exit(1)

    # Validar rate limit
    if requests_per_second > 4.0:
        console.print(
            "[yellow]Aviso: rate limit ajustado para 4.0 req/s (limite da API)[/yellow]"
        )
        requests_per_second = 4.0

    config = BatchAuditConfig(
        csv_file=csv_file,
        output_dir=output_dir,
        max_concurrent=max_concurrent,
        requests_per_second=requests_per_second,
        url_column=url_column,
        skip_recent_hours=skip_recent_hours,
        export_parquet=export_parquet,
        export_json=export_json,
    )

    console.print("[bold]Configuracao:[/bold]")
    console.print(f"  Rate limit: {requests_per_second} req/s")
    console.print(f"  Concorrencia: {max_concurrent}")
    console.print(
        f"  Coleta incremental: {skip_recent_hours}h"
        if skip_recent_hours > 0
        else "  Coleta incremental: desativada"
    )

    async def run_batch() -> None:
        processor = BatchProcessor(config, api_key)
        await processor.process()

    asyncio.run(run_batch())


@app.command()
def serve(
    port: int = typer.Option(8000, help="Porta do servidor"),
    host: str = typer.Option("localhost", help="Host do servidor"),
    db_path: str = typer.Option(
        "./data/sites_prefeituras.duckdb", help="Caminho do banco"
    ),
) -> None:
    """Inicia servidor web para visualização dos dados."""
    console.print(f"🚀 Iniciando servidor em [bold]http://{host}:{port}[/bold]")

    # NOTE: Visualização será via MkDocs com DuckDB-wasm
    # Os dados serão consultados diretamente do Internet Archive via HTTP
    console.print("⚠️ Servidor de visualização ainda não implementado")
    console.print("📚 Use 'uv run mkdocs serve' para visualizar a documentação")
    console.print(
        "🔮 Futura implementação: MkDocs + DuckDB-wasm + consultas HTTP ao IA"
    )


@app.command()
def stats(
    db_path: str = typer.Option(
        "./data/sites_prefeituras.duckdb", help="Caminho do banco"
    ),
) -> None:
    """Mostra estatísticas dos dados coletados."""

    async def show_stats() -> None:
        storage = DuckDBStorage(db_path)
        await storage.initialize()

        # Estatísticas básicas
        total_audits = storage._fetch_scalar("SELECT COUNT(*) FROM audits")
        total_errors = storage._fetch_scalar(
            "SELECT COUNT(*) FROM audits WHERE error_message IS NOT NULL"
        )

        # Últimas auditorias
        recent = (
            storage._get_conn()
            .execute("""
            SELECT url, timestamp,
                   CASE WHEN error_message IS NULL THEN '✅' ELSE '❌' END as status
            FROM audits
            ORDER BY timestamp DESC
            LIMIT 10
        """)
            .fetchall()
        )

        await storage.close()

        # Exibir estatísticas
        table = Table(title="📊 Estatísticas do Banco de Dados")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Total de Auditorias", str(total_audits))
        table.add_row("Auditorias com Erro", str(total_errors))
        table.add_row(
            "Taxa de Sucesso",
            f"{((total_audits - total_errors) / total_audits * 100):.1f}%"
            if total_audits > 0
            else "0%",
        )

        console.print(table)

        # Últimas auditorias
        if recent:
            recent_table = Table(title="🕒 Últimas Auditorias")
            recent_table.add_column("URL", style="blue")
            recent_table.add_column("Timestamp", style="yellow")
            recent_table.add_column("Status", style="green")

            for url, timestamp, status in recent:
                recent_table.add_row(
                    url[:50] + "..." if len(url) > 50 else url, str(timestamp), status
                )

            console.print(recent_table)

    asyncio.run(show_stats())


@app.command()
def cleanup(
    remove_js: bool = typer.Option(
        False, "--remove-js", help="Remove arquivos JavaScript"
    ),
    remove_node_modules: bool = typer.Option(
        False, "--remove-node-modules", help="Remove node_modules"
    ),
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirma remoção sem perguntar"
    ),
) -> None:
    """Limpa arquivos JavaScript e dependências Node.js."""

    if not remove_js and not remove_node_modules:
        console.print(
            "ℹ️ Use --remove-js e/ou --remove-node-modules para especificar o que remover"
        )
        return

    files_to_remove = []

    if remove_js:
        # Arquivos JavaScript a serem removidos
        js_files = [
            "collector/collect-psi.js",
            "package.json",
            "package-lock.json",
            ".nvmrc",
            "index.html",  # HTML estático antigo
        ]
        files_to_remove.extend(js_files)

    if remove_node_modules:
        files_to_remove.append("node_modules/")

    # Verificar quais arquivos existem
    existing_files = []
    for file_path in files_to_remove:
        full_path = Path(file_path)
        if full_path.exists():
            existing_files.append(str(full_path))

    if not existing_files:
        console.print("✅ Nenhum arquivo JavaScript encontrado para remover")
        return

    # Mostrar arquivos que serão removidos
    console.print("🗑️ Arquivos que serão removidos:")
    for file_path in existing_files:
        console.print(f"  - {file_path}")

    if not confirm:
        confirm_removal = typer.confirm("Confirma a remoção destes arquivos?")
        if not confirm_removal:
            console.print("❌ Operação cancelada")
            return

    # Remover arquivos
    for file_path in existing_files:
        try:
            path = Path(file_path)
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            console.print(f"Removido: {file_path}")
        except PermissionError as e:
            console.print(f"[red]Erro de permissao ao remover {file_path}: {e}[/red]")
        except OSError as e:
            console.print(f"[red]Erro ao remover {file_path}: {e}[/red]")

    console.print("Limpeza concluida! Projeto agora e 100% Python")


@app.command()
def metrics(
    db_path: str = typer.Option(
        "./data/sites_prefeituras.duckdb", help="Caminho do banco"
    ),
    by_state: bool = typer.Option(False, "--by-state", help="Agrupar por estado"),
    worst: int = typer.Option(
        0, "--worst", help="Mostrar N piores sites em performance"
    ),
    best: int = typer.Option(
        0, "--best", help="Mostrar N melhores sites em acessibilidade"
    ),
    export_json: str = typer.Option(
        None, "--export", help="Exportar metricas para arquivo JSON"
    ),
) -> None:
    """Mostra metricas agregadas das auditorias."""

    async def show_metrics() -> None:
        storage = DuckDBStorage(db_path)
        await storage.initialize()

        if by_state:
            # Metricas por estado
            state_metrics = await storage.get_metrics_by_state()

            if not state_metrics:
                console.print("[yellow]Nenhum dado por estado encontrado[/yellow]")
                return

            table = Table(title="Metricas por Estado")
            table.add_column("Estado", style="cyan")
            table.add_column("Sites", style="green")
            table.add_column("Perf. Media", style="yellow")
            table.add_column("Acess. Media", style="blue")

            for state_item in state_metrics[:20]:
                perf = (
                    f"{state_item['avg_performance'] * 100:.0f}%"
                    if state_item["avg_performance"]
                    else "N/A"
                )
                acc = (
                    f"{state_item['avg_accessibility'] * 100:.0f}%"
                    if state_item["avg_accessibility"]
                    else "N/A"
                )
                table.add_row(
                    state_item["state"] or "??",
                    str(state_item["site_count"]),
                    perf,
                    acc,
                )

            console.print(table)

        elif worst > 0:
            # Piores sites
            worst_sites = await storage.get_worst_performing_sites(limit=worst)

            table = Table(title=f"Top {worst} Piores Sites (Performance)")
            table.add_column("#", style="dim")
            table.add_column("URL", style="red")
            table.add_column("Mobile", style="yellow")
            table.add_column("Desktop", style="blue")

            for i, site in enumerate(worst_sites, 1):
                mobile = (
                    f"{site['mobile_performance'] * 100:.0f}%"
                    if site["mobile_performance"]
                    else "N/A"
                )
                desktop = (
                    f"{site['desktop_performance'] * 100:.0f}%"
                    if site["desktop_performance"]
                    else "N/A"
                )
                url = site["url"][:60] + "..." if len(site["url"]) > 60 else site["url"]
                table.add_row(str(i), url, mobile, desktop)

            console.print(table)

        elif best > 0:
            # Melhores sites em acessibilidade
            best_sites = await storage.get_best_accessibility_sites(limit=best)

            table = Table(title=f"Top {best} Melhores Sites (Acessibilidade)")
            table.add_column("#", style="dim")
            table.add_column("URL", style="green")
            table.add_column("Mobile", style="yellow")
            table.add_column("Desktop", style="blue")

            for i, acc_site in enumerate(best_sites, 1):
                mobile = (
                    f"{acc_site['mobile_accessibility'] * 100:.0f}%"
                    if acc_site["mobile_accessibility"]
                    else "N/A"
                )
                desktop = (
                    f"{acc_site['desktop_accessibility'] * 100:.0f}%"
                    if acc_site["desktop_accessibility"]
                    else "N/A"
                )
                url = (
                    acc_site["url"][:60] + "..."
                    if len(acc_site["url"]) > 60
                    else acc_site["url"]
                )
                table.add_row(str(i), url, mobile, desktop)

            console.print(table)

        else:
            # Metricas gerais
            m = await storage.get_aggregated_metrics()

            table = Table(title="Metricas Agregadas")
            table.add_column("Metrica", style="cyan")
            table.add_column("Valor", style="green")

            table.add_row("Total de auditorias", str(m["total_audits"]))
            table.add_row("Taxa de sucesso", f"{m['success_rate'] * 100:.1f}%")
            table.add_row("Taxa de erro", f"{m['error_rate'] * 100:.1f}%")
            table.add_row("", "")
            table.add_row(
                "Performance Mobile (media)",
                f"{m['avg_mobile_performance'] * 100:.1f}%"
                if m["avg_mobile_performance"]
                else "N/A",
            )
            table.add_row(
                "Performance Desktop (media)",
                f"{m['avg_desktop_performance'] * 100:.1f}%"
                if m["avg_desktop_performance"]
                else "N/A",
            )
            table.add_row(
                "Acessibilidade Mobile (media)",
                f"{m['avg_mobile_accessibility'] * 100:.1f}%"
                if m["avg_mobile_accessibility"]
                else "N/A",
            )
            table.add_row(
                "Acessibilidade Desktop (media)",
                f"{m['avg_desktop_accessibility'] * 100:.1f}%"
                if m["avg_desktop_accessibility"]
                else "N/A",
            )

            console.print(table)

            if export_json:
                await storage.export_aggregated_metrics_json(Path(export_json))
                console.print(f"Metricas exportadas para {export_json}")

        await storage.close()

    asyncio.run(show_metrics())


@app.command()
def quarantine(
    db_path: str = typer.Option(
        "./data/sites_prefeituras.duckdb", help="Caminho do banco"
    ),
    update: bool = typer.Option(
        False, "--update", help="Atualizar lista de quarentena"
    ),
    min_days: int = typer.Option(
        3, "--min-days", help="Minimo de dias com falha para quarentena"
    ),
    status: str = typer.Option(None, "--status", help="Filtrar por status"),
    set_status: str = typer.Option(
        None, "--set-status", help="Definir status de uma URL"
    ),
    url: str = typer.Option(None, "--url", help="URL para operacoes"),
    remove: bool = typer.Option(False, "--remove", help="Remover URL da quarentena"),
    export_json: str = typer.Option(None, "--export-json", help="Exportar para JSON"),
    export_csv: str = typer.Option(None, "--export-csv", help="Exportar para CSV"),
) -> None:
    """Gerencia sites em quarentena (falhas persistentes)."""

    async def manage_quarantine() -> None:
        storage = DuckDBStorage(db_path)
        await storage.initialize()

        if export_json:
            # Exportar para JSON
            result = await storage.export_quarantine_json(Path(export_json))
            console.print(
                f"[green]Quarentena exportada: {result['file']} ({result['count']} sites)[/green]"
            )
            await storage.close()
            return

        if export_csv:
            # Exportar para CSV
            result = await storage.export_quarantine_csv(Path(export_csv))
            console.print(
                f"[green]Quarentena exportada: {result['file']} ({result['count']} sites)[/green]"
            )
            await storage.close()
            return

        if update:
            # Atualizar quarentena
            update_result = await storage.update_quarantine(
                min_consecutive_days=min_days
            )
            console.print("[green]Quarentena atualizada:[/green]")
            console.print(f"  Adicionados: {update_result['added']}")
            console.print(f"  Atualizados: {update_result['updated']}")

        elif set_status and url:
            # Definir status
            success = await storage.update_quarantine_status(url, set_status)
            if success:
                console.print(
                    f"[green]Status atualizado: {url} -> {set_status}[/green]"
                )
            else:
                console.print("[red]URL nao encontrada na quarentena[/red]")

        elif remove and url:
            # Remover da quarentena
            success = await storage.remove_from_quarantine(url)
            if success:
                console.print(f"[green]Removido da quarentena: {url}[/green]")
            else:
                console.print("[red]URL nao encontrada na quarentena[/red]")

        else:
            # Listar quarentena
            stats = await storage.get_quarantine_stats()
            sites = await storage.get_quarantined_sites(status=status)

            # Stats
            stats_table = Table(title="Estatisticas da Quarentena")
            stats_table.add_column("Status", style="cyan")
            stats_table.add_column("Quantidade", style="green")

            stats_table.add_row("Total", str(stats["total"]))
            stats_table.add_row("Em quarentena", str(stats["quarantined"]))
            stats_table.add_row("Investigando", str(stats["investigating"]))
            stats_table.add_row("Resolvidos", str(stats["resolved"]))
            stats_table.add_row("URL errada", str(stats["wrong_url"]))
            stats_table.add_row("", "")
            stats_table.add_row("Media de falhas", str(stats["avg_failures"]))
            stats_table.add_row("Max falhas", str(stats["max_failures"]))

            console.print(stats_table)

            if sites:
                console.print("")
                sites_table = Table(title=f"Sites em Quarentena ({len(sites)})")
                sites_table.add_column("URL", style="red", max_width=50)
                sites_table.add_column("Falhas", style="yellow")
                sites_table.add_column("Ultima Falha", style="dim")
                sites_table.add_column("Status", style="cyan")
                sites_table.add_column("Erro", style="dim", max_width=30)

                for s in sites[:30]:
                    url_display = (
                        s["url"][:47] + "..." if len(s["url"]) > 50 else s["url"]
                    )
                    error = (
                        (s["last_error"] or "")[:27] + "..."
                        if s["last_error"] and len(s["last_error"]) > 30
                        else (s["last_error"] or "")
                    )
                    sites_table.add_row(
                        url_display,
                        str(s["consecutive_failures"]),
                        s["last_failure"][:10] if s["last_failure"] else "",
                        s["status"],
                        error,
                    )

                console.print(sites_table)

                if len(sites) > 30:
                    console.print(f"[dim]... e mais {len(sites) - 30} sites[/dim]")

        await storage.close()

    asyncio.run(manage_quarantine())


@app.command("export-dashboard")
def export_dashboard(
    db_path: str = typer.Option(
        "./data/sites_prefeituras.duckdb", help="Caminho do banco"
    ),
    output_dir: str = typer.Option("./docs/data", help="Diretorio de saida"),
) -> None:
    """Exporta JSONs estaticos para o dashboard (substitui DuckDB WASM)."""

    async def do_export() -> None:
        storage = DuckDBStorage(db_path)
        await storage.initialize()

        output_path = Path(output_dir)
        stats = await storage.export_dashboard_json(output_path)

        console.print("[green]Dashboard exportado:[/green]")
        console.print(f"  Diretorio: {output_dir}")
        console.print(f"  Total de sites: {stats.get('total_sites', 0)}")
        console.print("  Arquivos gerados:")
        for f in stats.get("files", []):
            console.print(f"    - {Path(f).name}")

        await storage.close()

    asyncio.run(do_export())


def _format_score(categories: dict, category_name: str) -> str:
    """Format a category score for display."""
    category = categories.get(category_name, {})
    score = category.score if category else None
    if score is not None:
        return f"{score * 100:.0f}"
    return "N/A"


def _display_audit_result(audit: "SiteAudit") -> None:
    """Exibe resultado da auditoria no console."""
    table = Table(title=f"Auditoria: {audit.url}")
    table.add_column("Metrica", style="cyan")
    table.add_column("Mobile", style="green")
    table.add_column("Desktop", style="blue")

    if audit.error_message:
        console.print(f"[red]Erro: {audit.error_message}[/red]")
        return

    # Extrair scores se disponíveis
    mobile_perf = mobile_acc = "N/A"
    desktop_perf = desktop_acc = "N/A"

    if audit.mobile_result:
        cats = audit.mobile_result.lighthouseResult.categories
        mobile_perf = _format_score(cats, "performance")
        mobile_acc = _format_score(cats, "accessibility")

    if audit.desktop_result:
        cats = audit.desktop_result.lighthouseResult.categories
        desktop_perf = _format_score(cats, "performance")
        desktop_acc = _format_score(cats, "accessibility")

    table.add_row("Performance", mobile_perf, desktop_perf)
    table.add_row("Accessibility", mobile_acc, desktop_acc)

    console.print(table)


if __name__ == "__main__":
    app()
