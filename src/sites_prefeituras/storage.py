"""Sistema de armazenamento com Ibis + DuckDB.

Design: All tables are APPEND-ONLY for data integrity and audit trails.
- audits: Each audit is a point-in-time snapshot (naturally append-only)
- audit_summaries: Derived from audits (naturally append-only)
- quarantine: Versioned records - each change creates new row with incremented version
  Use quarantine_current view to get latest state per URL
"""

import asyncio
import csv
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import ibis
from ibis import _
from rich.console import Console

from .models import AuditSummary, LighthouseAudit, SiteAudit
from .schemas import create_tables, get_table

# ============================================================================
# TypedDicts for structured return types
# ============================================================================


class AggregatedMetrics(TypedDict, total=False):
    """Structured type for aggregated metrics."""

    total_audits: int
    successful_audits: int
    failed_audits: int
    success_rate: float
    error_rate: float
    avg_mobile_performance: float | None
    avg_desktop_performance: float | None
    avg_mobile_accessibility: float | None
    avg_desktop_accessibility: float | None
    avg_mobile_seo: float | None
    avg_desktop_seo: float | None
    avg_mobile_best_practices: float | None
    avg_desktop_best_practices: float | None
    std_mobile_performance: float | None
    std_desktop_performance: float | None
    min_mobile_performance: float | None
    max_mobile_performance: float | None
    generated_at: str


class StateMetrics(TypedDict):
    """Structured type for state metrics."""

    state: str
    site_count: int
    avg_performance: float | None
    avg_accessibility: float | None


class SitePerformance(TypedDict):
    """Structured type for site performance data."""

    url: str
    mobile_performance: float | None
    desktop_performance: float | None
    mobile_accessibility: float | None
    timestamp: str | None


class SiteAccessibility(TypedDict):
    """Structured type for site accessibility data."""

    url: str
    mobile_accessibility: float | None
    desktop_accessibility: float | None
    mobile_performance: float | None
    timestamp: str | None


class TemporalData(TypedDict):
    """Structured type for temporal evolution data."""

    timestamp: str | None
    mobile_performance: float | None
    desktop_performance: float | None
    mobile_accessibility: float | None
    desktop_accessibility: float | None


class QuarantineUpdateStats(TypedDict):
    """Structured type for quarantine update statistics."""

    added: int
    updated: int
    total_checked: int


class QuarantineSite(TypedDict):
    """Structured type for quarantined site data."""

    url: str
    first_failure: str | None
    last_failure: str | None
    consecutive_failures: int
    last_error: str | None
    status: str
    notes: str | None
    created_at: str | None


class QuarantineStats(TypedDict):
    """Structured type for quarantine statistics."""

    total: int
    quarantined: int
    investigating: int
    resolved: int
    wrong_url: int
    avg_failures: float
    max_failures: int


class ExportStats(TypedDict):
    """Structured type for export statistics."""

    file: str
    count: int


class DashboardExportStats(TypedDict):
    """Structured type for dashboard export statistics."""

    generated_at: str
    files: list[str]
    total_sites: int


logger = logging.getLogger(__name__)
console = Console()


class DuckDBStorage:
    """Sistema de armazenamento usando Ibis com backend DuckDB."""

    def __init__(self, db_path: str = "./data/sites_prefeituras.duckdb") -> None:
        self.db_path: Path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._con: ibis.BaseBackend | None = None

    @property
    def con(self) -> ibis.BaseBackend:
        """Get Ibis connection, raising if not initialized."""
        if self._con is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._con

    @property
    def conn(self) -> "_IbisConnectionWrapper":
        """Backward-compatible connection wrapper for tests.

        Provides a .execute() method that accepts SQL with ? parameters.
        """
        return _IbisConnectionWrapper(self.con)

    def _get_next_id(self, table_name: str) -> int:
        """Get next ID for a table (DuckDB requires explicit IDs)."""
        t = get_table(self.con, table_name)
        result = t.id.max().execute()
        return (result or 0) + 1

    async def initialize(self) -> None:
        """Inicializa o banco de dados e cria tabelas."""

        def connect_and_create() -> ibis.BaseBackend:
            con = ibis.duckdb.connect(str(self.db_path))
            create_tables(con)
            return con

        self._con = await asyncio.to_thread(connect_and_create)
        logger.info("Database tables initialized via Ibis")

    # ========================================================================
    # Table accessors (Ibis tables)
    # ========================================================================

    @property
    def audits(self) -> ibis.Table:
        """Get audits table."""
        return get_table(self.con, "audits")

    @property
    def summaries(self) -> ibis.Table:
        """Get audit_summaries table."""
        return get_table(self.con, "audit_summaries")

    @property
    def quarantine_table(self) -> ibis.Table:
        """Get quarantine base table (all versions)."""
        return get_table(self.con, "quarantine")

    @property
    def quarantine_current(self) -> ibis.Table:
        """Get current quarantine state view (latest version per URL)."""
        return get_table(self.con, "quarantine_current")

    def _get_next_version(self, url: str) -> int:
        """Get next version number for a URL in quarantine."""
        t = self.quarantine_table
        result = t.filter(t.url == url).version.max().execute()
        return (result or 0) + 1

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def save_audit(self, audit: SiteAudit) -> int:
        """Salva uma auditoria completa."""

        def insert_audit() -> int:
            next_id = self._get_next_id("audits")

            # Prepare data for insert
            data = {
                "id": [next_id],
                "url": [str(audit.url)],
                "timestamp": [audit.timestamp],
                "mobile_result": [
                    audit.mobile_result.model_dump_json()
                    if audit.mobile_result
                    else None
                ],
                "desktop_result": [
                    audit.desktop_result.model_dump_json()
                    if audit.desktop_result
                    else None
                ],
                "error_message": [audit.error_message],
                "retry_count": [audit.retry_count],
                "created_at": [datetime.utcnow()],
            }

            # Use Ibis memtable for insert
            mem = ibis.memtable(data)
            self.con.insert("audits", mem)
            return next_id

        audit_id = await asyncio.to_thread(insert_audit)

        # Criar e salvar resumo
        summary = self._create_summary(audit)
        await self._save_summary(summary)

        return audit_id

    def _create_summary(self, audit: SiteAudit) -> AuditSummary:
        """Cria resumo a partir de auditoria completa."""
        summary = AuditSummary(
            url=audit.url,
            timestamp=audit.timestamp,
            has_errors=audit.error_message is not None,
            error_message=audit.error_message,
        )

        # Extrair scores mobile
        if audit.mobile_result:
            scores = self._extract_category_scores(
                audit.mobile_result.lighthouseResult.categories
            )
            summary.mobile_performance = scores["performance"]
            summary.mobile_accessibility = scores["accessibility"]
            summary.mobile_best_practices = scores["best_practices"]
            summary.mobile_seo = scores["seo"]

            # Core Web Vitals mobile
            vitals = self._extract_web_vitals(
                audit.mobile_result.lighthouseResult.audits
            )
            summary.mobile_fcp = vitals["fcp"]
            summary.mobile_lcp = vitals["lcp"]
            summary.mobile_cls = vitals["cls"]
            summary.mobile_fid = vitals["fid"]

        # Extrair scores desktop
        if audit.desktop_result:
            scores = self._extract_category_scores(
                audit.desktop_result.lighthouseResult.categories
            )
            summary.desktop_performance = scores["performance"]
            summary.desktop_accessibility = scores["accessibility"]
            summary.desktop_best_practices = scores["best_practices"]
            summary.desktop_seo = scores["seo"]

            # Core Web Vitals desktop
            vitals = self._extract_web_vitals(
                audit.desktop_result.lighthouseResult.audits
            )
            summary.desktop_fcp = vitals["fcp"]
            summary.desktop_lcp = vitals["lcp"]
            summary.desktop_cls = vitals["cls"]
            summary.desktop_fid = vitals["fid"]

        return summary

    def _extract_category_scores(self, categories: dict) -> dict[str, float | None]:
        """Extract scores from Lighthouse categories."""
        return {
            "performance": categories.get("performance", {}).score,
            "accessibility": categories.get("accessibility", {}).score,
            "best_practices": categories.get("best-practices", {}).score,
            "seo": categories.get("seo", {}).score,
        }

    def _extract_web_vitals(
        self, audits: dict[str, LighthouseAudit]
    ) -> dict[str, float | None]:
        """Extract Core Web Vitals from Lighthouse audits."""
        return {
            "fcp": self._extract_metric_value(audits.get("first-contentful-paint")),
            "lcp": self._extract_metric_value(audits.get("largest-contentful-paint")),
            "cls": self._extract_metric_value(audits.get("cumulative-layout-shift")),
            "fid": self._extract_metric_value(audits.get("max-potential-fid")),
        }

    def _extract_metric_value(self, audit_data: LighthouseAudit | None) -> float | None:
        """Extrai valor numérico de uma métrica."""
        if audit_data and hasattr(audit_data, "numericValue"):
            return audit_data.numericValue
        return None

    async def _save_summary(self, summary: AuditSummary) -> None:
        """Salva resumo da auditoria."""

        def insert_summary() -> None:
            next_id = self._get_next_id("audit_summaries")

            data = {
                "id": [next_id],
                "url": [str(summary.url)],
                "timestamp": [summary.timestamp],
                "mobile_performance": [summary.mobile_performance],
                "mobile_accessibility": [summary.mobile_accessibility],
                "mobile_best_practices": [summary.mobile_best_practices],
                "mobile_seo": [summary.mobile_seo],
                "desktop_performance": [summary.desktop_performance],
                "desktop_accessibility": [summary.desktop_accessibility],
                "desktop_best_practices": [summary.desktop_best_practices],
                "desktop_seo": [summary.desktop_seo],
                "mobile_fcp": [summary.mobile_fcp],
                "mobile_lcp": [summary.mobile_lcp],
                "mobile_cls": [summary.mobile_cls],
                "mobile_fid": [summary.mobile_fid],
                "desktop_fcp": [summary.desktop_fcp],
                "desktop_lcp": [summary.desktop_lcp],
                "desktop_cls": [summary.desktop_cls],
                "desktop_fid": [summary.desktop_fid],
                "has_errors": [summary.has_errors],
                "error_message": [summary.error_message],
                "created_at": [datetime.utcnow()],
            }

            mem = ibis.memtable(data)
            self.con.insert("audit_summaries", mem)

        await asyncio.to_thread(insert_summary)

    async def get_recently_audited_urls(self, hours: int = 24) -> set[str]:
        """Retorna URLs auditadas nas ultimas N horas (para coleta incremental)."""

        def query_recent() -> set[str]:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            # Ibis query
            result = (
                self.audits.filter((_.timestamp > cutoff) & (_.error_message.isnull()))
                .select("url")
                .distinct()
                .execute()
            )

            return set(result["url"].tolist())

        urls = await asyncio.to_thread(query_recent)
        logger.info(f"Found {len(urls)} URLs audited in last {hours} hours")
        return urls

    async def export_to_parquet(self, output_dir: Path) -> None:
        """Exporta dados para arquivos Parquet particionados."""
        output_dir.mkdir(exist_ok=True)

        def export_parquet() -> None:
            # Export audits with date partition
            audits_df = (
                self.audits.mutate(date_partition=_.timestamp.truncate("D"))
                .select(
                    "url", "timestamp", "error_message", "retry_count", "date_partition"
                )
                .execute()
            )

            if not audits_df.empty:
                for date, group in audits_df.groupby("date_partition"):
                    date_str = date.strftime("%Y-%m-%d")
                    parquet_file = output_dir / f"audits_date={date_str}.parquet"
                    group.drop("date_partition", axis=1).to_parquet(parquet_file)

            # Export summaries
            summaries_df = self.summaries.execute()
            if not summaries_df.empty:
                summaries_file = output_dir / "audit_summaries.parquet"
                summaries_df.to_parquet(summaries_file)

        await asyncio.to_thread(export_parquet)
        console.print(f"Dados exportados para {output_dir}")

    async def export_to_json(self, output_dir: Path) -> None:
        """Exporta dados para JSON (para visualização web)."""
        output_dir.mkdir(exist_ok=True)

        def export_json() -> None:
            # Query using Ibis
            result = (
                self.summaries.select(
                    "url",
                    "timestamp",
                    "mobile_performance",
                    "desktop_performance",
                    "mobile_accessibility",
                    "desktop_accessibility",
                    "has_errors",
                    "error_message",
                )
                .order_by(ibis.desc("timestamp"))
                .limit(1000)
                .execute()
            )

            json_data = {
                "last_updated": datetime.utcnow().isoformat(),
                "total_sites": len(result),
                "audits": [
                    {
                        "url": row["url"],
                        "timestamp": row["timestamp"].isoformat()
                        if row["timestamp"]
                        else None,
                        "mobile_performance": row["mobile_performance"],
                        "desktop_performance": row["desktop_performance"],
                        "mobile_accessibility": row["mobile_accessibility"],
                        "desktop_accessibility": row["desktop_accessibility"],
                        "has_errors": row["has_errors"],
                        "error_message": row["error_message"],
                    }
                    for _, row in result.iterrows()
                ],
            }

            json_file = output_dir / "latest_audits.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(export_json)
        console.print(f"JSON exportado para {output_dir / 'latest_audits.json'}")

    # ========================================================================
    # Metricas agregadas
    # ========================================================================

    async def get_aggregated_metrics(self) -> AggregatedMetrics:
        """Retorna metricas agregadas de todas as auditorias."""

        def query_metrics() -> AggregatedMetrics:
            t = self.summaries

            # Build aggregation query
            agg = t.aggregate(
                total_audits=t.count(),
                successful_audits=(~t.has_errors).sum(),
                failed_audits=t.has_errors.sum(),
                avg_mobile_performance=t.mobile_performance.mean(),
                avg_desktop_performance=t.desktop_performance.mean(),
                avg_mobile_accessibility=t.mobile_accessibility.mean(),
                avg_desktop_accessibility=t.desktop_accessibility.mean(),
                avg_mobile_seo=t.mobile_seo.mean(),
                avg_desktop_seo=t.desktop_seo.mean(),
                avg_mobile_best_practices=t.mobile_best_practices.mean(),
                avg_desktop_best_practices=t.desktop_best_practices.mean(),
                std_mobile_performance=t.mobile_performance.std(),
                std_desktop_performance=t.desktop_performance.std(),
                min_mobile_performance=t.mobile_performance.min(),
                max_mobile_performance=t.mobile_performance.max(),
            ).execute()

            # Handle empty result
            if agg.empty:
                return AggregatedMetrics(
                    total_audits=0,
                    successful_audits=0,
                    failed_audits=0,
                    success_rate=0.0,
                    error_rate=0.0,
                )

            row = agg.iloc[0]
            total = int(row["total_audits"]) if row["total_audits"] else 0
            successful = (
                int(row["successful_audits"]) if row["successful_audits"] else 0
            )
            failed = int(row["failed_audits"]) if row["failed_audits"] else 0

            return AggregatedMetrics(
                total_audits=total,
                successful_audits=successful,
                failed_audits=failed,
                success_rate=successful / total if total > 0 else 0,
                error_rate=failed / total if total > 0 else 0,
                avg_mobile_performance=row["avg_mobile_performance"],
                avg_desktop_performance=row["avg_desktop_performance"],
                avg_mobile_accessibility=row["avg_mobile_accessibility"],
                avg_desktop_accessibility=row["avg_desktop_accessibility"],
                avg_mobile_seo=row["avg_mobile_seo"],
                avg_desktop_seo=row["avg_desktop_seo"],
                avg_mobile_best_practices=row["avg_mobile_best_practices"],
                avg_desktop_best_practices=row["avg_desktop_best_practices"],
                std_mobile_performance=row["std_mobile_performance"],
                std_desktop_performance=row["std_desktop_performance"],
                min_mobile_performance=row["min_mobile_performance"],
                max_mobile_performance=row["max_mobile_performance"],
            )

        return await asyncio.to_thread(query_metrics)

    async def get_metrics_by_state(self) -> list[StateMetrics]:
        """Retorna metricas agregadas por estado (extraido da URL)."""

        def query_by_state() -> list[StateMetrics]:
            t = self.summaries

            # Extract state from URL using regex
            # Pattern: .XX.gov.br where XX is the state code
            result = (
                t.filter(~t.has_errors)
                .mutate(state=t.url.re_extract(r"\.([a-z]{2})\.gov\.br", 1).upper())
                .filter(_.state.notnull() & (_.state != ""))
                .group_by("state")
                .aggregate(
                    site_count=_.count(),
                    avg_performance=_.mobile_performance.mean(),
                    avg_accessibility=_.mobile_accessibility.mean(),
                )
                .order_by(ibis.desc("avg_performance"))
                .execute()
            )

            return [
                StateMetrics(
                    state=row["state"],
                    site_count=int(row["site_count"]),
                    avg_performance=row["avg_performance"],
                    avg_accessibility=row["avg_accessibility"],
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_by_state)

    async def get_worst_performing_sites(
        self, limit: int = 10
    ) -> list[SitePerformance]:
        """Retorna os sites com pior performance."""

        def query_worst() -> list[SitePerformance]:
            result = (
                self.summaries.filter(
                    (~self.summaries.has_errors)
                    & self.summaries.mobile_performance.notnull()
                )
                .select(
                    "url",
                    "mobile_performance",
                    "desktop_performance",
                    "mobile_accessibility",
                    "timestamp",
                )
                .order_by("mobile_performance")
                .limit(limit)
                .execute()
            )

            return [
                SitePerformance(
                    url=row["url"],
                    mobile_performance=row["mobile_performance"],
                    desktop_performance=row["desktop_performance"],
                    mobile_accessibility=row["mobile_accessibility"],
                    timestamp=row["timestamp"].isoformat()
                    if row["timestamp"]
                    else None,
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_worst)

    async def get_best_accessibility_sites(
        self, limit: int = 10
    ) -> list[SiteAccessibility]:
        """Retorna os sites com melhor acessibilidade."""

        def query_best() -> list[SiteAccessibility]:
            result = (
                self.summaries.filter(
                    (~self.summaries.has_errors)
                    & self.summaries.mobile_accessibility.notnull()
                )
                .select(
                    "url",
                    "mobile_accessibility",
                    "desktop_accessibility",
                    "mobile_performance",
                    "timestamp",
                )
                .order_by(ibis.desc("mobile_accessibility"))
                .limit(limit)
                .execute()
            )

            return [
                SiteAccessibility(
                    url=row["url"],
                    mobile_accessibility=row["mobile_accessibility"],
                    desktop_accessibility=row["desktop_accessibility"],
                    mobile_performance=row["mobile_performance"],
                    timestamp=row["timestamp"].isoformat()
                    if row["timestamp"]
                    else None,
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_best)

    async def get_temporal_evolution(self, url: str) -> list[TemporalData]:
        """Retorna evolucao temporal de metricas para uma URL."""
        # Normalize URL (Pydantic HttpUrl adds trailing slash)
        normalized_url = url.rstrip("/") + "/"

        def query_temporal() -> list[TemporalData]:
            t = self.summaries
            # Try both with and without trailing slash for compatibility
            result = (
                t.filter((t.url.isin([url, normalized_url])) & (~t.has_errors))
                .select(
                    "timestamp",
                    "mobile_performance",
                    "desktop_performance",
                    "mobile_accessibility",
                    "desktop_accessibility",
                )
                .order_by("timestamp")
                .execute()
            )

            return [
                TemporalData(
                    timestamp=row["timestamp"].isoformat()
                    if row["timestamp"]
                    else None,
                    mobile_performance=row["mobile_performance"],
                    desktop_performance=row["desktop_performance"],
                    mobile_accessibility=row["mobile_accessibility"],
                    desktop_accessibility=row["desktop_accessibility"],
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_temporal)

    async def export_aggregated_metrics_json(self, output_file: Path) -> None:
        """Exporta metricas agregadas para JSON."""
        metrics = await self.get_aggregated_metrics()
        metrics["generated_at"] = datetime.utcnow().isoformat()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        logger.info(f"Aggregated metrics exported to {output_file}")

    # ========================================================================
    # Sistema de Quarentena
    # ========================================================================

    async def update_quarantine(
        self, min_consecutive_days: int = 3
    ) -> QuarantineUpdateStats:
        """
        Atualiza a lista de quarentena baseado em falhas consecutivas.

        Sites que falharam por N dias consecutivos sao adicionados a quarentena.
        Isso ajuda a identificar URLs que podem ter mudado ou estao incorretas.

        APPEND-ONLY: New records are inserted; existing records preserved for audit.

        Args:
            min_consecutive_days: Minimo de dias com falha para entrar em quarentena

        Returns:
            Estatisticas da atualizacao
        """
        lookback_days = int(min_consecutive_days * 2)
        min_failures = int(min_consecutive_days)

        def update_quarantine_sync() -> QuarantineUpdateStats:
            # This complex query with window functions is best done via raw SQL
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            now = datetime.utcnow()

            # Find sites with consecutive failures
            query = f"""
            WITH daily_failures AS (
                SELECT DISTINCT
                    url,
                    DATE(timestamp) as failure_date,
                    MAX(error_message) as error_message
                FROM audits
                WHERE error_message IS NOT NULL
                  AND timestamp >= '{cutoff.strftime("%Y-%m-%d")}'
                GROUP BY url, DATE(timestamp)
            ),
            numbered AS (
                SELECT
                    url,
                    failure_date,
                    error_message,
                    failure_date - INTERVAL (ROW_NUMBER() OVER (
                        PARTITION BY url ORDER BY failure_date
                    )) DAY as grp
                FROM daily_failures
            ),
            consecutive_sequences AS (
                SELECT
                    url,
                    MIN(failure_date) as first_failure,
                    MAX(failure_date) as last_failure,
                    COUNT(*) as consecutive_days,
                    MAX(error_message) as last_error
                FROM numbered
                GROUP BY url, grp
                HAVING COUNT(*) >= {min_failures}
            ),
            best_sequence AS (
                SELECT
                    url,
                    first_failure,
                    last_failure,
                    consecutive_days,
                    last_error,
                    ROW_NUMBER() OVER (PARTITION BY url ORDER BY consecutive_days DESC) as rn
                FROM consecutive_sequences
            )
            SELECT url, first_failure, last_failure, consecutive_days, last_error
            FROM best_sequence
            WHERE rn = 1
            """

            results = self.con.raw_sql(query).fetchall()

            added = 0
            updated = 0

            for url, first_failure, last_failure, failure_days, last_error in results:
                # Check current state in quarantine using the current view
                existing = (
                    self.quarantine_current.filter(self.quarantine_current.url == url)
                    .select(
                        "version", "consecutive_failures", "first_failure", "status"
                    )
                    .execute()
                )

                if not existing.empty:
                    # URL already in quarantine - append new version if data changed
                    current = existing.iloc[0]
                    current_failures = current["consecutive_failures"]

                    # Only insert new version if failure count changed
                    if current_failures != failure_days:
                        next_id = self._get_next_id("quarantine")
                        next_version = int(current["version"]) + 1
                        # Preserve original first_failure from earliest record
                        original_first = current["first_failure"]

                        data = {
                            "id": [next_id],
                            "url": [url],
                            "first_failure": [original_first],
                            "last_failure": [last_failure],
                            "consecutive_failures": [failure_days],
                            "last_error_message": [last_error],
                            "status": [current["status"]],  # Preserve status
                            "notes": [None],
                            "version": [next_version],
                            "valid_from": [now],
                            "created_at": [now],
                        }
                        mem = ibis.memtable(data)
                        self.con.insert("quarantine", mem)
                        updated += 1
                else:
                    # New URL - insert first version
                    next_id = self._get_next_id("quarantine")
                    data = {
                        "id": [next_id],
                        "url": [url],
                        "first_failure": [first_failure],
                        "last_failure": [last_failure],
                        "consecutive_failures": [failure_days],
                        "last_error_message": [last_error],
                        "status": ["quarantined"],
                        "notes": [None],
                        "version": [1],
                        "valid_from": [now],
                        "created_at": [now],
                    }
                    mem = ibis.memtable(data)
                    self.con.insert("quarantine", mem)
                    added += 1

            return QuarantineUpdateStats(
                added=added, updated=updated, total_checked=len(results)
            )

        stats = await asyncio.to_thread(update_quarantine_sync)
        logger.info(
            f"Quarantine updated: {stats['added']} added, {stats['updated']} updated"
        )
        return stats

    async def get_quarantined_sites(
        self,
        status: str | None = None,
        min_failures: int = 0,
    ) -> list[QuarantineSite]:
        """
        Retorna sites em quarentena (current state only).

        Uses the quarantine_current view which shows latest version per URL.

        Args:
            status: Filtrar por status (quarantined, investigating, resolved)
            min_failures: Minimo de falhas consecutivas

        Returns:
            Lista de sites em quarentena
        """

        def query_quarantine() -> list[QuarantineSite]:
            # Use current view for latest state
            t = self.quarantine_current

            # Build filter - exclude "removed" status by default
            query = t.filter(
                (t.consecutive_failures >= min_failures) & (t.status != "removed")
            )

            if status:
                query = query.filter(t.status == status)

            result = (
                query.select(
                    "url",
                    "first_failure",
                    "last_failure",
                    "consecutive_failures",
                    "last_error_message",
                    "status",
                    "notes",
                    "created_at",
                )
                .order_by(
                    ibis.desc("consecutive_failures"),
                    ibis.desc("last_failure"),
                )
                .execute()
            )

            return [
                QuarantineSite(
                    url=row["url"],
                    first_failure=row["first_failure"].isoformat()
                    if row["first_failure"]
                    else None,
                    last_failure=row["last_failure"].isoformat()
                    if row["last_failure"]
                    else None,
                    consecutive_failures=int(row["consecutive_failures"]),
                    last_error=row["last_error_message"],
                    status=row["status"],
                    notes=row["notes"],
                    created_at=row["created_at"].isoformat()
                    if row["created_at"]
                    else None,
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_quarantine)

    async def update_quarantine_status(
        self,
        url: str,
        status: str,
        notes: str | None = None,
    ) -> bool:
        """
        Atualiza status de um site na quarentena.

        APPEND-ONLY: Inserts new version with updated status.

        Args:
            url: URL do site
            status: Novo status (quarantined, investigating, resolved, wrong_url)
            notes: Notas opcionais

        Returns:
            True se atualizado, False se nao encontrado
        """
        valid_statuses = ["quarantined", "investigating", "resolved", "wrong_url"]
        if status not in valid_statuses:
            raise ValueError(f"Status invalido. Use: {valid_statuses}")

        def update_status() -> bool:
            now = datetime.utcnow()

            # Get current state from view
            existing = self.quarantine_current.filter(
                self.quarantine_current.url == url
            ).execute()

            if existing.empty:
                return False

            current = existing.iloc[0]

            # Insert new version with updated status (append-only)
            next_id = self._get_next_id("quarantine")
            next_version = int(current["version"]) + 1

            data = {
                "id": [next_id],
                "url": [url],
                "first_failure": [current["first_failure"]],
                "last_failure": [current["last_failure"]],
                "consecutive_failures": [int(current["consecutive_failures"])],
                "last_error_message": [current["last_error_message"]],
                "status": [status],
                "notes": [notes],
                "version": [next_version],
                "valid_from": [now],
                "created_at": [now],
            }
            mem = ibis.memtable(data)
            self.con.insert("quarantine", mem)

            logger.info(
                f"Quarantine status updated: {url} -> {status} (v{next_version})"
            )
            return True

        return await asyncio.to_thread(update_status)

    async def remove_from_quarantine(self, url: str) -> bool:
        """Remove um site da quarentena.

        APPEND-ONLY: Inserts new version with status='removed'.
        The URL will be filtered out from active queries.
        """

        def remove() -> bool:
            now = datetime.utcnow()

            # Get current state from view
            existing = self.quarantine_current.filter(
                self.quarantine_current.url == url
            ).execute()

            if existing.empty:
                return False

            current = existing.iloc[0]

            # Insert new version with "removed" status (append-only)
            next_id = self._get_next_id("quarantine")
            next_version = int(current["version"]) + 1

            data = {
                "id": [next_id],
                "url": [url],
                "first_failure": [current["first_failure"]],
                "last_failure": [current["last_failure"]],
                "consecutive_failures": [int(current["consecutive_failures"])],
                "last_error_message": [current["last_error_message"]],
                "status": ["removed"],
                "notes": ["Removed from quarantine"],
                "version": [next_version],
                "valid_from": [now],
                "created_at": [now],
            }
            mem = ibis.memtable(data)
            self.con.insert("quarantine", mem)

            logger.info(f"Removed from quarantine: {url} (v{next_version})")
            return True

        return await asyncio.to_thread(remove)

    async def get_quarantine_stats(self) -> QuarantineStats:
        """Retorna estatisticas da quarentena (current state only)."""

        def query_stats() -> QuarantineStats:
            # Use current view - exclude removed entries
            t = self.quarantine_current
            t_active = t.filter(t.status != "removed")

            # Aggregate stats
            result = t_active.aggregate(
                total=t_active.count(),
                quarantined=(t_active.status == "quarantined").sum(),
                investigating=(t_active.status == "investigating").sum(),
                resolved=(t_active.status == "resolved").sum(),
                wrong_url=(t_active.status == "wrong_url").sum(),
                avg_failures=t_active.consecutive_failures.mean(),
                max_failures=t_active.consecutive_failures.max(),
            ).execute()

            if result.empty:
                return QuarantineStats(
                    total=0,
                    quarantined=0,
                    investigating=0,
                    resolved=0,
                    wrong_url=0,
                    avg_failures=0.0,
                    max_failures=0,
                )

            row = result.iloc[0]
            return QuarantineStats(
                total=int(row["total"]) if row["total"] else 0,
                quarantined=int(row["quarantined"]) if row["quarantined"] else 0,
                investigating=int(row["investigating"]) if row["investigating"] else 0,
                resolved=int(row["resolved"]) if row["resolved"] else 0,
                wrong_url=int(row["wrong_url"]) if row["wrong_url"] else 0,
                avg_failures=round(row["avg_failures"], 1)
                if row["avg_failures"]
                else 0.0,
                max_failures=int(row["max_failures"]) if row["max_failures"] else 0,
            )

        return await asyncio.to_thread(query_stats)

    async def get_urls_to_skip_quarantine(self) -> set[str]:
        """Retorna URLs em quarentena que devem ser puladas na coleta."""

        def query_skip() -> set[str]:
            # Use current view for latest state
            t = self.quarantine_current
            result = (
                t.filter(t.status.isin(["quarantined", "wrong_url"]))
                .select("url")
                .execute()
            )
            return set(result["url"].tolist())

        return await asyncio.to_thread(query_skip)

    async def export_quarantine_json(self, output_file: Path) -> ExportStats:
        """
        Exporta lista de quarentena para JSON.

        Args:
            output_file: Caminho do arquivo de saida

        Returns:
            Estatisticas da exportacao
        """
        sites = await self.get_quarantined_sites()
        stats = await self.get_quarantine_stats()

        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "stats": stats,
            "sites": sites,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)

        def write_json() -> None:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(write_json)

        logger.info(f"Quarantine exported to {output_file}: {len(sites)} sites")
        return ExportStats(file=str(output_file), count=len(sites))

    async def export_quarantine_csv(self, output_file: Path) -> ExportStats:
        """
        Exporta lista de quarentena para CSV.

        Args:
            output_file: Caminho do arquivo de saida

        Returns:
            Estatisticas da exportacao
        """
        sites = await self.get_quarantined_sites()

        output_file.parent.mkdir(parents=True, exist_ok=True)

        def write_csv() -> None:
            with open(output_file, "w", encoding="utf-8", newline="") as f:
                if sites:
                    writer = csv.DictWriter(f, fieldnames=list(sites[0].keys()))
                    writer.writeheader()
                    writer.writerows(sites)

        await asyncio.to_thread(write_csv)

        logger.info(f"Quarantine CSV exported to {output_file}: {len(sites)} sites")
        return ExportStats(file=str(output_file), count=len(sites))

    # ========================================================================
    # Exportacao para Dashboard (JSON estatico - substitui WASM)
    # ========================================================================

    async def export_dashboard_json(self, output_dir: Path) -> DashboardExportStats:
        """
        Exporta todos os JSONs necessarios para o dashboard.

        Substitui o DuckDB WASM por arquivos JSON estaticos.
        Gera:
        - summary.json: Metricas agregadas
        - ranking.json: Ranking completo de sites
        - by-state.json: Agrupado por estado
        - top50.json: Melhores 50 sites
        - worst50.json: Piores 50 sites

        Args:
            output_dir: Diretorio de saida

        Returns:
            Estatisticas da exportacao
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.utcnow().isoformat()
        files: list[str] = []

        # 1. Summary - Metricas agregadas
        summary_file = await self._export_summary(output_dir, generated_at)
        files.append(str(summary_file))

        # 2. Ranking completo (ultimas auditorias de cada site)
        ranking, ranking_file = await self._export_ranking(output_dir, generated_at)
        files.append(str(ranking_file))

        # 3. Top 50 e Worst 50
        top50_file, worst50_file = await self._export_top_worst(
            output_dir, generated_at, ranking
        )
        files.extend([str(top50_file), str(worst50_file)])

        # 4. Por estado
        by_state_file = await self._export_by_state(output_dir, generated_at)
        files.append(str(by_state_file))

        # 5. Quarentena
        quarantine_file = await self._export_quarantine_dashboard(
            output_dir, generated_at
        )
        files.append(str(quarantine_file))

        logger.info(f"Dashboard JSON exported to {output_dir}: {len(files)} files")
        console.print(f"Dashboard JSON exportado: {output_dir} ({len(ranking)} sites)")

        return DashboardExportStats(
            generated_at=generated_at,
            files=files,
            total_sites=len(ranking),
        )

    async def _export_summary(self, output_dir: Path, generated_at: str) -> Path:
        """Export summary metrics to JSON."""
        summary = dict(await self.get_aggregated_metrics())
        summary["generated_at"] = generated_at
        summary_file = output_dir / "summary.json"

        def write_file() -> None:
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(write_file)
        return summary_file

    async def _export_ranking(
        self, output_dir: Path, generated_at: str
    ) -> tuple[list[dict], Path]:
        """Export ranking data to JSON."""

        def query_ranking() -> list[dict]:
            # Use window function for ranking - requires raw SQL for full support
            query = """
            WITH latest AS (
                SELECT
                    url,
                    timestamp,
                    mobile_accessibility,
                    mobile_performance,
                    mobile_seo,
                    mobile_best_practices,
                    desktop_accessibility,
                    desktop_performance,
                    mobile_fcp,
                    mobile_lcp,
                    mobile_cls,
                    has_errors,
                    ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) as rn
                FROM audit_summaries
                WHERE NOT has_errors
            )
            SELECT
                url,
                timestamp,
                mobile_accessibility as accessibility_score,
                mobile_performance as performance_score,
                mobile_seo as seo_score,
                mobile_best_practices as best_practices_score,
                desktop_accessibility,
                desktop_performance,
                mobile_fcp as fcp,
                mobile_lcp as lcp,
                mobile_cls as cls,
                RANK() OVER (ORDER BY mobile_accessibility DESC NULLS LAST) as rank
            FROM latest
            WHERE rn = 1
            ORDER BY mobile_accessibility DESC NULLS LAST
            """

            result = self.con.raw_sql(query).fetchall()

            return [
                {
                    "url": row[0],
                    "name": self._extract_name_from_url(row[0]),
                    "state": self._extract_state_from_url(row[0]),
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "score": round((row[2] or 0) * 100, 1),
                    "performance": round((row[3] or 0) * 100, 1),
                    "seo": round((row[4] or 0) * 100, 1),
                    "best_practices": round((row[5] or 0) * 100, 1),
                    "desktop_accessibility": round((row[6] or 0) * 100, 1)
                    if row[6]
                    else None,
                    "desktop_performance": round((row[7] or 0) * 100, 1)
                    if row[7]
                    else None,
                    "fcp": row[8],
                    "lcp": row[9],
                    "cls": row[10],
                    "rank": row[11],
                }
                for row in result
            ]

        ranking = await asyncio.to_thread(query_ranking)

        ranking_file = output_dir / "ranking.json"
        ranking_output = {
            "generated_at": generated_at,
            "total": len(ranking),
            "sites": ranking,
        }

        def write_file() -> None:
            with open(ranking_file, "w", encoding="utf-8") as f:
                json.dump(ranking_output, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(write_file)
        return ranking, ranking_file

    async def _export_top_worst(
        self, output_dir: Path, generated_at: str, ranking: list[dict]
    ) -> tuple[Path, Path]:
        """Export top 50 and worst 50 sites to JSON."""
        top50 = ranking[:50]
        worst50 = sorted(ranking, key=lambda x: x["score"])[:50]

        top50_file = output_dir / "top50.json"
        worst50_file = output_dir / "worst50.json"

        def write_files() -> None:
            with open(top50_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"generated_at": generated_at, "sites": top50},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            with open(worst50_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"generated_at": generated_at, "sites": worst50},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        await asyncio.to_thread(write_files)
        return top50_file, worst50_file

    async def _export_by_state(self, output_dir: Path, generated_at: str) -> Path:
        """Export metrics by state to JSON."""
        by_state = await self.get_metrics_by_state()
        by_state_file = output_dir / "by-state.json"

        def write_file() -> None:
            with open(by_state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"generated_at": generated_at, "states": by_state},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        await asyncio.to_thread(write_file)
        return by_state_file

    async def _export_quarantine_dashboard(
        self, output_dir: Path, generated_at: str
    ) -> Path:
        """Export quarantine data for dashboard."""
        quarantine = await self.get_quarantined_sites()
        quarantine_stats = await self.get_quarantine_stats()
        quarantine_file = output_dir / "quarantine.json"

        def write_file() -> None:
            with open(quarantine_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "generated_at": generated_at,
                        "stats": quarantine_stats,
                        "sites": quarantine,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        await asyncio.to_thread(write_file)
        return quarantine_file

    def _extract_name_from_url(self, url: str) -> str:
        """Extrai nome amigavel de uma URL."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or url
            # Remove www. e .gov.br
            name = hostname.replace("www.", "")
            # Remove sufixos comuns
            for suffix in [".gov.br", ".org.br", ".com.br"]:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
            return name
        except ValueError:
            # Invalid URL format
            return url

    def _extract_state_from_url(self, url: str) -> str:
        """Extrai estado de uma URL .gov.br."""
        match = re.search(r"\.([a-z]{2})\.gov\.br", url.lower())
        if match:
            return match.group(1).upper()
        return "N/A"

    async def close(self) -> None:
        """Fecha conexao com banco."""
        if self._con:
            self._con.disconnect()
            self._con = None


class _IbisConnectionWrapper:
    """Wrapper to provide conn.execute() interface for Ibis backend.

    This provides backward compatibility for tests that use the old
    duckdb connection.execute() pattern.
    """

    def __init__(self, ibis_con: ibis.BaseBackend):
        self._con = ibis_con

    def execute(self, query: str, params: list | None = None) -> None:
        """Execute SQL with optional parameters.

        Args:
            query: SQL query with ? placeholders
            params: List of parameter values to substitute
        """
        if params:
            # Format query with parameters (simplified for tests)
            formatted_query = query
            for param in params:
                if param is None:
                    formatted_query = formatted_query.replace("?", "NULL", 1)
                elif isinstance(param, str):
                    safe_param = param.replace("'", "''")
                    formatted_query = formatted_query.replace("?", f"'{safe_param}'", 1)
                elif isinstance(param, (int, float)):
                    formatted_query = formatted_query.replace("?", str(param), 1)
                else:
                    # For datetime and other types
                    formatted_query = formatted_query.replace("?", f"'{param}'", 1)
            self._con.raw_sql(formatted_query)
        else:
            self._con.raw_sql(query)
