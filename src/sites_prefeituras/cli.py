"""Interface de linha de comando para Sites Prefeituras."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from .collector import audit_single_site, audit_batch, BatchProcessor
from .models import BatchAuditConfig
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
        console.print("Configure com: [bold]export PAGESPEED_API_KEY='sua_chave'[/bold]")
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
    
    async def run_audit():
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
    output_dir: str = typer.Option("./output", help="Diretório de saída"),
    max_concurrent: int = typer.Option(5, help="Máximo de requisições simultâneas"),
    requests_per_second: float = typer.Option(1.0, help="Taxa de requisições por segundo"),
    url_column: str = typer.Option("url", help="Nome da coluna com URLs"),
    export_parquet: bool = typer.Option(True, help="Exportar para Parquet"),
    export_json: bool = typer.Option(True, help="Exportar para JSON"),
) -> None:
    """Executa auditoria em lote a partir de arquivo CSV."""
    api_key = get_api_key()
    
    if not Path(csv_file).exists():
        console.print(f"❌ [red]Arquivo não encontrado: {csv_file}[/red]")
        raise typer.Exit(1)
    
    config = BatchAuditConfig(
        csv_file=csv_file,
        output_dir=output_dir,
        max_concurrent=max_concurrent,
        requests_per_second=requests_per_second,
        url_column=url_column,
        export_parquet=export_parquet,
        export_json=export_json,
    )
    
    async def run_batch():
        processor = BatchProcessor(config, api_key)
        await processor.process()
    
    asyncio.run(run_batch())


@app.command()
def serve(
    port: int = typer.Option(8000, help="Porta do servidor"),
    host: str = typer.Option("localhost", help="Host do servidor"),
    db_path: str = typer.Option("./data/sites_prefeituras.duckdb", help="Caminho do banco"),
) -> None:
    """Inicia servidor web para visualização dos dados."""
    console.print(f"🚀 Iniciando servidor em [bold]http://{host}:{port}[/bold]")

    # NOTE: Visualização será via MkDocs com DuckDB-wasm
    # Os dados serão consultados diretamente do Internet Archive via HTTP
    console.print("⚠️ Servidor de visualização ainda não implementado")
    console.print("📚 Use 'uv run mkdocs serve' para visualizar a documentação")
    console.print("🔮 Futura implementação: MkDocs + DuckDB-wasm + consultas HTTP ao IA")


@app.command()
def stats(
    db_path: str = typer.Option("./data/sites_prefeituras.duckdb", help="Caminho do banco"),
) -> None:
    """Mostra estatísticas dos dados coletados."""
    
    async def show_stats():
        storage = DuckDBStorage(db_path)
        await storage.initialize()
        
        # Estatísticas básicas
        total_audits = storage.conn.execute("SELECT COUNT(*) FROM audits").fetchone()[0]
        total_errors = storage.conn.execute("SELECT COUNT(*) FROM audits WHERE error_message IS NOT NULL").fetchone()[0]
        
        # Últimas auditorias
        recent = storage.conn.execute("""
            SELECT url, timestamp, 
                   CASE WHEN error_message IS NULL THEN '✅' ELSE '❌' END as status
            FROM audits 
            ORDER BY timestamp DESC 
            LIMIT 10
        """).fetchall()
        
        await storage.close()
        
        # Exibir estatísticas
        table = Table(title="📊 Estatísticas do Banco de Dados")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Total de Auditorias", str(total_audits))
        table.add_row("Auditorias com Erro", str(total_errors))
        table.add_row("Taxa de Sucesso", f"{((total_audits - total_errors) / total_audits * 100):.1f}%" if total_audits > 0 else "0%")
        
        console.print(table)
        
        # Últimas auditorias
        if recent:
            recent_table = Table(title="🕒 Últimas Auditorias")
            recent_table.add_column("URL", style="blue")
            recent_table.add_column("Timestamp", style="yellow")
            recent_table.add_column("Status", style="green")
            
            for url, timestamp, status in recent:
                recent_table.add_row(url[:50] + "..." if len(url) > 50 else url, 
                                   str(timestamp), status)
            
            console.print(recent_table)
    
    asyncio.run(show_stats())


@app.command()
def cleanup(
    remove_js: bool = typer.Option(False, "--remove-js", help="Remove arquivos JavaScript"),
    remove_node_modules: bool = typer.Option(False, "--remove-node-modules", help="Remove node_modules"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirma remoção sem perguntar"),
) -> None:
    """Limpa arquivos JavaScript e dependências Node.js."""
    
    if not remove_js and not remove_node_modules:
        console.print("ℹ️ Use --remove-js e/ou --remove-node-modules para especificar o que remover")
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
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
            console.print(f"✅ Removido: {file_path}")
        except Exception as e:
            console.print(f"❌ Erro ao remover {file_path}: {e}")
    
    console.print("🎉 Limpeza concluída! Projeto agora é 100% Python")


def _display_audit_result(audit) -> None:
    """Exibe resultado da auditoria no console."""
    table = Table(title=f"📊 Auditoria: {audit.url}")
    table.add_column("Métrica", style="cyan")
    table.add_column("Mobile", style="green")
    table.add_column("Desktop", style="blue")
    
    if audit.error_message:
        console.print(f"❌ [red]Erro: {audit.error_message}[/red]")
        return
    
    # Extrair scores se disponíveis
    mobile_perf = desktop_perf = "N/A"
    mobile_acc = desktop_acc = "N/A"
    
    if audit.mobile_result:
        cats = audit.mobile_result.lighthouseResult.categories
        mobile_perf = f"{cats.get('performance', {}).score * 100:.0f}" if cats.get('performance', {}).score else "N/A"
        mobile_acc = f"{cats.get('accessibility', {}).score * 100:.0f}" if cats.get('accessibility', {}).score else "N/A"
    
    if audit.desktop_result:
        cats = audit.desktop_result.lighthouseResult.categories
        desktop_perf = f"{cats.get('performance', {}).score * 100:.0f}" if cats.get('performance', {}).score else "N/A"
        desktop_acc = f"{cats.get('accessibility', {}).score * 100:.0f}" if cats.get('accessibility', {}).score else "N/A"
    
    table.add_row("Performance", mobile_perf, desktop_perf)
    table.add_row("Accessibility", mobile_acc, desktop_acc)
    
    console.print(table)


if __name__ == "__main__":
    app()