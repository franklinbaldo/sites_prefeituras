"""Coletor de dados do PageSpeed Insights - substitui o collector Node.js."""

import asyncio
import csv
import logging
from pathlib import Path
from typing import List, Optional, AsyncGenerator
from urllib.parse import urlparse

import httpx
from asyncio_throttle import Throttler
from rich.console import Console
from rich.progress import Progress, TaskID
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import PageSpeedInsightsResult, SiteAudit, BatchAuditConfig
from .storage import DuckDBStorage

logger = logging.getLogger(__name__)
console = Console()


class PageSpeedCollector:
    """Coletor async para PageSpeed Insights API."""
    
    def __init__(
        self,
        api_key: str,
        requests_per_second: float = 1.0,
        max_concurrent: int = 5,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.throttler = Throttler(rate_limit=requests_per_second)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        
    async def __aenter__(self):
        """Context manager entry."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _fetch_pagespeed_data(
        self, 
        url: str, 
        strategy: str = "mobile"
    ) -> PageSpeedInsightsResult:
        """Busca dados do PageSpeed Insights para uma URL e estratégia."""
        params = {
            "url": url,
            "key": self.api_key,
            "strategy": strategy,
            "category": ["performance", "accessibility", "best-practices", "seo"],
        }
        
        async with self.throttler:
            async with self.semaphore:
                logger.debug(f"Fetching PSI data for {url} ({strategy})")
                
                response = await self.client.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return PageSpeedInsightsResult(**data)
    
    async def audit_site(self, url: str) -> SiteAudit:
        """Audita um site completo (mobile + desktop)."""
        audit = SiteAudit(url=url)
        
        try:
            # Buscar dados mobile e desktop em paralelo
            tasks = [
                self._fetch_pagespeed_data(url, "mobile"),
                self._fetch_pagespeed_data(url, "desktop"),
            ]
            
            mobile_result, desktop_result = await asyncio.gather(*tasks)
            
            audit.mobile_result = mobile_result
            audit.desktop_result = desktop_result
            
        except Exception as e:
            logger.error(f"Error auditing {url}: {e}")
            audit.error_message = str(e)
            
        return audit
    
    async def audit_from_csv(
        self,
        csv_file: Path,
        config: BatchAuditConfig,
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None,
        skip_urls: Optional[set[str]] = None,
    ) -> AsyncGenerator[SiteAudit, None]:
        """Audita sites a partir de arquivo CSV."""
        all_urls = await self._read_urls_from_csv(csv_file, config.url_column)

        # Filtrar URLs já auditadas (coleta incremental)
        if skip_urls:
            urls = [u for u in all_urls if u not in skip_urls]
            skipped = len(all_urls) - len(urls)
            if skipped > 0:
                logger.info(f"Skipped {skipped} recently audited URLs")
        else:
            urls = all_urls

        if progress and task_id:
            progress.update(task_id, total=len(urls))

        for url in urls:
            try:
                audit = await self.audit_site(url)
                yield audit

                if progress and task_id:
                    progress.update(task_id, advance=1)

            except Exception as e:
                logger.error(f"Failed to audit {url}: {e}")
                yield SiteAudit(url=url, error_message=str(e))
    
    async def _read_urls_from_csv(self, csv_file: Path, url_column: str) -> List[str]:
        """Lê URLs de arquivo CSV."""
        urls = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if url_column in row and row[url_column]:
                    url = row[url_column].strip()
                    if self._is_valid_url(url):
                        urls.append(url)
                    else:
                        logger.warning(f"Invalid URL skipped: {url}")
        
        logger.info(f"Loaded {len(urls)} valid URLs from {csv_file}")
        return urls
    
    def _is_valid_url(self, url: str) -> bool:
        """Valida se uma URL é válida."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class BatchProcessor:
    """Processador para auditorias em lote."""

    def __init__(self, config: BatchAuditConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        self.storage = DuckDBStorage()

    async def process(self) -> None:
        """Executa processamento em lote completo."""
        csv_file = Path(self.config.csv_file)
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(exist_ok=True)

        console.print(f"[bold]Iniciando auditoria em lote de {csv_file}[/bold]")
        console.print(f"Saida: [bold]{output_dir}[/bold]")

        # Inicializar storage
        await self.storage.initialize()

        # Coleta incremental: buscar URLs já auditadas recentemente
        skip_urls: set[str] = set()
        if self.config.skip_recent_hours > 0:
            skip_urls = await self.storage.get_recently_audited_urls(
                hours=self.config.skip_recent_hours
            )
            if skip_urls:
                console.print(
                    f"[yellow]Pulando {len(skip_urls)} sites auditados nas ultimas "
                    f"{self.config.skip_recent_hours}h[/yellow]"
                )

        # Progress bar
        with Progress() as progress:
            task = progress.add_task("Auditando sites...", total=None)

            async with PageSpeedCollector(
                api_key=self.api_key,
                requests_per_second=self.config.requests_per_second,
                max_concurrent=self.config.max_concurrent,
            ) as collector:

                audit_count = 0
                error_count = 0
                skipped_count = 0

                async for audit in collector.audit_from_csv(
                    csv_file, self.config, progress, task, skip_urls=skip_urls
                ):
                    # Salvar no DuckDB
                    await self.storage.save_audit(audit)

                    audit_count += 1
                    if audit.error_message:
                        error_count += 1

                    # Log progresso
                    if audit_count % 50 == 0:
                        console.print(
                            f"Processados: {audit_count} | "
                            f"Erros: {error_count}"
                        )
        
        # Exportar dados
        if self.config.export_parquet:
            await self._export_parquet(output_dir)

        if self.config.export_json:
            await self._export_json(output_dir)

        console.print(f"🎉 Processamento concluído!")
        console.print(f"📊 Total processado: {audit_count}")
        console.print(f"❌ Erros: {error_count}")
        
    async def _export_parquet(self, output_dir: Path) -> None:
        """Exporta dados para formato Parquet."""
        console.print("📦 Exportando para Parquet...")
        await self.storage.export_to_parquet(output_dir)
        
    async def _export_json(self, output_dir: Path) -> None:
        """Exporta dados para formato JSON."""
        console.print("📄 Exportando para JSON...")
        await self.storage.export_to_json(output_dir)


# ============================================================================
# Funcoes de processamento paralelo
# ============================================================================

def chunked(iterable: List, size: int):
    """Divide uma lista em chunks de tamanho especificado."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


async def process_urls_in_chunks(
    collector: PageSpeedCollector,
    urls: List[str],
    chunk_size: int = 10,
) -> List[SiteAudit]:
    """
    Processa URLs em chunks paralelos, respeitando rate limit.

    O throttler e semaphore do collector controlam o rate limit real.
    O chunk_size controla quantas coroutines sao criadas por vez.

    Args:
        collector: Instancia do PageSpeedCollector (ja com rate limit configurado)
        urls: Lista de URLs para auditar
        chunk_size: Tamanho do chunk (quantas URLs processar em paralelo)

    Returns:
        Lista de SiteAudit com resultados
    """
    all_results: List[SiteAudit] = []

    for chunk in chunked(urls, chunk_size):
        # Criar tasks para todas URLs do chunk
        tasks = [collector.audit_site(url) for url in chunk]

        # Processar chunk em paralelo (rate limit controlado pelo throttler)
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Processar resultados
        for url, result in zip(chunk, chunk_results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {url}: {result}")
                all_results.append(SiteAudit(url=url, error_message=str(result)))
            else:
                all_results.append(result)

    return all_results


# ============================================================================
# Funcoes de conveniencia
# ============================================================================

async def audit_single_site(url: str, api_key: str) -> SiteAudit:
    """Audita um unico site - funcao de conveniencia."""
    async with PageSpeedCollector(api_key=api_key) as collector:
        return await collector.audit_site(url)


async def audit_batch(csv_file: str, api_key: str, **kwargs) -> None:
    """Audita sites em lote - funcao de conveniencia."""
    config = BatchAuditConfig(csv_file=csv_file, **kwargs)
    processor = BatchProcessor(config, api_key)
    await processor.process()