"""Sistema de armazenamento com DuckDB via Ibis - substitui a lógica Node.js."""

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
import ibis.backends.duckdb
from rich.console import Console

from .models import AuditSummary, LighthouseAudit, SiteAudit

# ============================================================================
# TypedDicts for structured return types
# ============================================================================


class AggregatedMetrics(TypedDict):
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

# ============================================================================
# Ibis Schema Definitions
# ============================================================================

AUDITS_SCHEMA = ibis.schema(
    {
        "id": "int64",
        "url": "string",
        "timestamp": "timestamp",
        "mobile_result": "string",  # JSON stored as string
        "desktop_result": "string",  # JSON stored as string
        "error_message": "string",
        "retry_count": "int64",
        "created_at": "timestamp",
    }
)

AUDIT_SUMMARIES_SCHEMA = ibis.schema(
    {
        "id": "int64",
        "url": "string",
        "timestamp": "timestamp",
        # Scores principais (0-1)
        "mobile_performance": "float64",
        "mobile_accessibility": "float64",
        "mobile_best_practices": "float64",
        "mobile_seo": "float64",
        "desktop_performance": "float64",
        "desktop_accessibility": "float64",
        "desktop_best_practices": "float64",
        "desktop_seo": "float64",
        # Core Web Vitals
        "mobile_fcp": "float64",
        "mobile_lcp": "float64",
        "mobile_cls": "float64",
        "mobile_fid": "float64",
        "desktop_fcp": "float64",
        "desktop_lcp": "float64",
        "desktop_cls": "float64",
        "desktop_fid": "float64",
        # Status
        "has_errors": "boolean",
        "error_message": "string",
        "created_at": "timestamp",
    }
)

QUARANTINE_SCHEMA = ibis.schema(
    {
        "id": "int64",
        "url": "string",
        "first_failure": "timestamp",
        "last_failure": "timestamp",
        "consecutive_failures": "int64",
        "last_error_message": "string",
        "status": "string",
        "notes": "string",
        "created_at": "timestamp",
        "updated_at": "timestamp",
    }
)


class DuckDBStorage:
    """Sistema de armazenamento usando DuckDB via Ibis."""

    def __init__(self, db_path: str = "./data/sites_prefeituras.duckdb") -> None:
        self.db_path: Path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.con: ibis.backends.duckdb.Backend | None = None

    @property
    def conn(self) -> ibis.backends.duckdb.Backend | None:
        """Backward-compatible alias for con."""
        return self.con

    async def initialize(self) -> None:
        """Inicializa o banco de dados e cria tabelas."""

        def connect() -> ibis.backends.duckdb.Backend:
            return ibis.duckdb.connect(str(self.db_path))

        self.con = await asyncio.to_thread(connect)
        await self._create_tables()

    async def _create_tables(self) -> None:
        """Cria tabelas necessárias usando Ibis."""

        def create_tables() -> None:
            # Create audits table
            self.con.raw_sql("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY,
                    url VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    mobile_result JSON,
                    desktop_result JSON,
                    error_message VARCHAR,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create audit_summaries table
            self.con.raw_sql("""
                CREATE TABLE IF NOT EXISTS audit_summaries (
                    id INTEGER PRIMARY KEY,
                    url VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    mobile_performance DOUBLE,
                    mobile_accessibility DOUBLE,
                    mobile_best_practices DOUBLE,
                    mobile_seo DOUBLE,
                    desktop_performance DOUBLE,
                    desktop_accessibility DOUBLE,
                    desktop_best_practices DOUBLE,
                    desktop_seo DOUBLE,
                    mobile_fcp DOUBLE,
                    mobile_lcp DOUBLE,
                    mobile_cls DOUBLE,
                    mobile_fid DOUBLE,
                    desktop_fcp DOUBLE,
                    desktop_lcp DOUBLE,
                    desktop_cls DOUBLE,
                    desktop_fid DOUBLE,
                    has_errors BOOLEAN DEFAULT FALSE,
                    error_message VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create quarantine table
            self.con.raw_sql("""
                CREATE TABLE IF NOT EXISTS quarantine (
                    id INTEGER PRIMARY KEY,
                    url VARCHAR NOT NULL UNIQUE,
                    first_failure TIMESTAMP NOT NULL,
                    last_failure TIMESTAMP NOT NULL,
                    consecutive_failures INTEGER DEFAULT 1,
                    last_error_message VARCHAR,
                    status VARCHAR DEFAULT 'quarantined',
                    notes VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            self.con.raw_sql(
                "CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url)"
            )
            self.con.raw_sql(
                "CREATE INDEX IF NOT EXISTS idx_audits_timestamp ON audits(timestamp)"
            )
            self.con.raw_sql(
                "CREATE INDEX IF NOT EXISTS idx_summaries_url ON audit_summaries(url)"
            )
            self.con.raw_sql(
                "CREATE INDEX IF NOT EXISTS idx_quarantine_url ON quarantine(url)"
            )
            self.con.raw_sql(
                "CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine(status)"
            )

        await asyncio.to_thread(create_tables)
        logger.info("Database tables initialized")

    def _audits_table(self) -> ibis.Table:
        """Return the audits table."""
        return self.con.table("audits")

    def _summaries_table(self) -> ibis.Table:
        """Return the audit_summaries table."""
        return self.con.table("audit_summaries")

    def _quarantine_table(self) -> ibis.Table:
        """Return the quarantine table."""
        return self.con.table("quarantine")

    async def save_audit(self, audit: SiteAudit) -> int:
        """Salva uma auditoria completa."""

        def insert_audit() -> int:
            # Insert using raw SQL for RETURNING support
            result = self.con.raw_sql("""
                INSERT INTO audits (url, timestamp, mobile_result, desktop_result, error_message, retry_count)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, parameters=[
                str(audit.url),
                audit.timestamp,
                audit.mobile_result.model_dump_json() if audit.mobile_result else None,
                audit.desktop_result.model_dump_json() if audit.desktop_result else None,
                audit.error_message,
                audit.retry_count,
            ]).fetchone()
            return result[0] if result else 0

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

    def _extract_category_scores(
        self, categories: dict
    ) -> dict[str, float | None]:
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

    def _extract_metric_value(
        self, audit_data: LighthouseAudit | None
    ) -> float | None:
        """Extrai valor numérico de uma métrica."""
        if audit_data and hasattr(audit_data, "numericValue"):
            return audit_data.numericValue
        return None

    async def _save_summary(self, summary: AuditSummary) -> None:
        """Salva resumo da auditoria."""

        def insert_summary() -> None:
            self.con.raw_sql("""
                INSERT INTO audit_summaries (
                    url, timestamp,
                    mobile_performance, mobile_accessibility, mobile_best_practices, mobile_seo,
                    desktop_performance, desktop_accessibility, desktop_best_practices, desktop_seo,
                    mobile_fcp, mobile_lcp, mobile_cls, mobile_fid,
                    desktop_fcp, desktop_lcp, desktop_cls, desktop_fid,
                    has_errors, error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """, parameters=[
                str(summary.url), summary.timestamp,
                summary.mobile_performance, summary.mobile_accessibility,
                summary.mobile_best_practices, summary.mobile_seo,
                summary.desktop_performance, summary.desktop_accessibility,
                summary.desktop_best_practices, summary.desktop_seo,
                summary.mobile_fcp, summary.mobile_lcp, summary.mobile_cls, summary.mobile_fid,
                summary.desktop_fcp, summary.desktop_lcp, summary.desktop_cls, summary.desktop_fid,
                summary.has_errors, summary.error_message,
            ])

        await asyncio.to_thread(insert_summary)

    async def get_recently_audited_urls(self, hours: int = 24) -> set[str]:
        """Retorna URLs auditadas nas ultimas N horas (para coleta incremental)."""

        def query_urls() -> set[str]:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            audits = self._audits_table()

            result = (
                audits.filter(
                    (audits.timestamp > cutoff) & (audits.error_message.isnull())
                )
                .select("url")
                .distinct()
                .to_pandas()
            )

            return set(result["url"].tolist())

        urls = await asyncio.to_thread(query_urls)
        logger.info(f"Found {len(urls)} URLs audited in last {hours} hours")
        return urls

    async def export_to_parquet(self, output_dir: Path) -> None:
        """Exporta dados para arquivos Parquet particionados."""
        output_dir.mkdir(exist_ok=True)

        def export() -> None:
            audits = self._audits_table()
            audits_df = (
                audits.mutate(
                    date_partition=audits.timestamp.truncate("D")
                )
                .select("url", "timestamp", "error_message", "retry_count", "date_partition")
                .to_pandas()
            )

            if not audits_df.empty:
                for date, group in audits_df.groupby("date_partition"):
                    date_str = date.strftime("%Y-%m-%d")
                    parquet_file = output_dir / f"audits_date={date_str}.parquet"
                    group.drop("date_partition", axis=1).to_parquet(parquet_file)

            summaries_df = self._summaries_table().to_pandas()
            if not summaries_df.empty:
                summaries_file = output_dir / "audit_summaries.parquet"
                summaries_df.to_parquet(summaries_file)

        await asyncio.to_thread(export)
        console.print(f"Dados exportados para {output_dir}")

    async def export_to_json(self, output_dir: Path) -> None:
        """Exporta dados para JSON (para visualização web)."""
        output_dir.mkdir(exist_ok=True)

        def export() -> None:
            summaries = self._summaries_table()
            result = (
                summaries.select(
                    "url", "timestamp",
                    "mobile_performance", "desktop_performance",
                    "mobile_accessibility", "desktop_accessibility",
                    "has_errors", "error_message"
                )
                .order_by(ibis.desc("timestamp"))
                .limit(1000)
                .to_pandas()
            )

            json_data = {
                "last_updated": datetime.utcnow().isoformat(),
                "total_sites": len(result),
                "audits": [
                    {
                        "url": row["url"],
                        "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                        "mobile_performance": row["mobile_performance"],
                        "desktop_performance": row["desktop_performance"],
                        "mobile_accessibility": row["mobile_accessibility"],
                        "desktop_accessibility": row["desktop_accessibility"],
                        "has_errors": row["has_errors"],
                        "error_message": row["error_message"],
                    }
                    for _, row in result.iterrows()
                ]
            }

            json_file = output_dir / "latest_audits.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(export)
        console.print(f"JSON exportado para {output_dir}")

    # ========================================================================
    # Metricas agregadas
    # ========================================================================

    async def get_aggregated_metrics(self) -> AggregatedMetrics:
        """Retorna metricas agregadas de todas as auditorias."""

        def query_metrics() -> AggregatedMetrics:
            summaries = self._summaries_table()

            result = summaries.aggregate(
                total_audits=summaries.count(),
                successful_audits=summaries.has_errors.isin([False]).sum(),
                failed_audits=summaries.has_errors.sum(),
                avg_mobile_performance=summaries.mobile_performance.mean(),
                avg_desktop_performance=summaries.desktop_performance.mean(),
                avg_mobile_accessibility=summaries.mobile_accessibility.mean(),
                avg_desktop_accessibility=summaries.desktop_accessibility.mean(),
                avg_mobile_seo=summaries.mobile_seo.mean(),
                avg_desktop_seo=summaries.desktop_seo.mean(),
                avg_mobile_best_practices=summaries.mobile_best_practices.mean(),
                avg_desktop_best_practices=summaries.desktop_best_practices.mean(),
                std_mobile_performance=summaries.mobile_performance.std(),
                std_desktop_performance=summaries.desktop_performance.std(),
                min_mobile_performance=summaries.mobile_performance.min(),
                max_mobile_performance=summaries.mobile_performance.max(),
            ).to_pandas()

            row = result.iloc[0] if not result.empty else {}
            total = int(row.get("total_audits", 0) or 0)
            successful = int(row.get("successful_audits", 0) or 0)
            failed = int(row.get("failed_audits", 0) or 0)

            return AggregatedMetrics(
                total_audits=total,
                successful_audits=successful,
                failed_audits=failed,
                success_rate=successful / total if total > 0 else 0,
                error_rate=failed / total if total > 0 else 0,
                avg_mobile_performance=row.get("avg_mobile_performance"),
                avg_desktop_performance=row.get("avg_desktop_performance"),
                avg_mobile_accessibility=row.get("avg_mobile_accessibility"),
                avg_desktop_accessibility=row.get("avg_desktop_accessibility"),
                avg_mobile_seo=row.get("avg_mobile_seo"),
                avg_desktop_seo=row.get("avg_desktop_seo"),
                avg_mobile_best_practices=row.get("avg_mobile_best_practices"),
                avg_desktop_best_practices=row.get("avg_desktop_best_practices"),
                std_mobile_performance=row.get("std_mobile_performance"),
                std_desktop_performance=row.get("std_desktop_performance"),
                min_mobile_performance=row.get("min_mobile_performance"),
                max_mobile_performance=row.get("max_mobile_performance"),
            )

        return await asyncio.to_thread(query_metrics)

    async def get_metrics_by_state(self) -> list[StateMetrics]:
        """Retorna metricas agregadas por estado (extraido da URL)."""

        def query_by_state() -> list[StateMetrics]:
            summaries = self._summaries_table()

            # Extract state from URL using regex
            state_expr = summaries.url.re_extract(r"\.([a-z]{2})\.gov\.br", 1).upper()

            with_state = summaries.filter(~summaries.has_errors).mutate(state=state_expr)
            filtered = with_state.filter(
                with_state.state.notnull() & (with_state.state != "")
            )
            result = (
                filtered.group_by("state")
                .aggregate(
                    site_count=filtered.count(),
                    avg_performance=filtered.mobile_performance.mean(),
                    avg_accessibility=filtered.mobile_accessibility.mean(),
                )
                .order_by(ibis.desc("avg_performance"))
                .to_pandas()
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

    async def get_worst_performing_sites(self, limit: int = 10) -> list[SitePerformance]:
        """Retorna os sites com pior performance."""

        def query_worst() -> list[SitePerformance]:
            summaries = self._summaries_table()

            result = (
                summaries.filter(
                    ~summaries.has_errors & summaries.mobile_performance.notnull()
                )
                .select(
                    "url", "mobile_performance", "desktop_performance",
                    "mobile_accessibility", "timestamp"
                )
                .order_by("mobile_performance")
                .limit(limit)
                .to_pandas()
            )

            return [
                SitePerformance(
                    url=row["url"],
                    mobile_performance=row["mobile_performance"],
                    desktop_performance=row["desktop_performance"],
                    mobile_accessibility=row["mobile_accessibility"],
                    timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_worst)

    async def get_best_accessibility_sites(self, limit: int = 10) -> list[SiteAccessibility]:
        """Retorna os sites com melhor acessibilidade."""

        def query_best() -> list[SiteAccessibility]:
            summaries = self._summaries_table()

            result = (
                summaries.filter(
                    ~summaries.has_errors & summaries.mobile_accessibility.notnull()
                )
                .select(
                    "url", "mobile_accessibility", "desktop_accessibility",
                    "mobile_performance", "timestamp"
                )
                .order_by(ibis.desc("mobile_accessibility"))
                .limit(limit)
                .to_pandas()
            )

            return [
                SiteAccessibility(
                    url=row["url"],
                    mobile_accessibility=row["mobile_accessibility"],
                    desktop_accessibility=row["desktop_accessibility"],
                    mobile_performance=row["mobile_performance"],
                    timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
                )
                for _, row in result.iterrows()
            ]

        return await asyncio.to_thread(query_best)

    async def get_temporal_evolution(self, url: str) -> list[TemporalData]:
        """Retorna evolucao temporal de metricas para uma URL."""

        def query_temporal() -> list[TemporalData]:
            summaries = self._summaries_table()

            result = (
                summaries.filter(
                    (summaries.url == url) & ~summaries.has_errors
                )
                .select(
                    "timestamp", "mobile_performance", "desktop_performance",
                    "mobile_accessibility", "desktop_accessibility"
                )
                .order_by("timestamp")
                .to_pandas()
            )

            return [
                TemporalData(
                    timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
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
        metrics = dict(await self.get_aggregated_metrics())
        metrics["generated_at"] = datetime.utcnow().isoformat()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        logger.info(f"Aggregated metrics exported to {output_file}")

    # ========================================================================
    # Sistema de Quarentena
    # ========================================================================

    async def update_quarantine(self, min_consecutive_days: int = 3) -> QuarantineUpdateStats:
        """
        Atualiza a lista de quarentena baseado em falhas consecutivas.

        Sites que falharam por N dias consecutivos sao adicionados a quarentena.
        Isso ajuda a identificar URLs que podem ter mudado ou estao incorretas.

        Args:
            min_consecutive_days: Minimo de dias com falha para entrar em quarentena

        Returns:
            Estatisticas da atualizacao
        """

        def update_quarantine_sync() -> QuarantineUpdateStats:
            audits = self._audits_table()
            cutoff_date = datetime.utcnow().date() - timedelta(days=min_consecutive_days * 2)

            # Find sites with failures
            failures_base = audits.filter(audits.error_message.notnull())
            failures = failures_base.mutate(failure_date=failures_base.timestamp.date())
            failures = failures.filter(failures.failure_date >= cutoff_date)

            # Group by URL to get failure stats
            failure_stats_query = failures.group_by("url").aggregate(
                first_failure=failures.failure_date.min(),
                last_failure=failures.failure_date.max(),
                failure_days=failures.failure_date.nunique(),
            )
            failure_stats = (
                failure_stats_query.filter(
                    failure_stats_query.failure_days >= min_consecutive_days
                )
                .to_pandas()
            )

            # Get last error for each URL
            failures_with_rn = failures.mutate(
                rn=ibis.row_number().over(
                    ibis.window(group_by="url", order_by=ibis.desc("timestamp"))
                )
            )
            last_errors = (
                failures_with_rn.filter(failures_with_rn.rn == 0)
                .select("url", last_error="error_message")
                .to_pandas()
            )

            # Merge failure stats with last errors
            if not failure_stats.empty and not last_errors.empty:
                failure_stats = failure_stats.merge(last_errors, on="url", how="left")
            elif not failure_stats.empty:
                failure_stats["last_error"] = None

            added = 0
            updated = 0

            for _, row in failure_stats.iterrows():
                url = row["url"]
                first_failure = row["first_failure"]
                last_failure = row["last_failure"]
                failure_days = int(row["failure_days"])
                last_error = row.get("last_error")

                # Check if URL exists in quarantine
                quarantine = self._quarantine_table()
                existing = quarantine.filter(quarantine.url == url).to_pandas()

                if not existing.empty:
                    # Update existing record
                    self.con.raw_sql("""
                        UPDATE quarantine
                        SET last_failure = $1,
                            consecutive_failures = $2,
                            last_error_message = $3,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE url = $4
                    """, parameters=[last_failure, failure_days, last_error, url])
                    updated += 1
                else:
                    # Add new record
                    self.con.raw_sql("""
                        INSERT INTO quarantine (url, first_failure, last_failure,
                                               consecutive_failures, last_error_message)
                        VALUES ($1, $2, $3, $4, $5)
                    """, parameters=[url, first_failure, last_failure, failure_days, last_error])
                    added += 1

            return QuarantineUpdateStats(
                added=added, updated=updated, total_checked=len(failure_stats)
            )

        stats = await asyncio.to_thread(update_quarantine_sync)
        logger.info(f"Quarantine updated: {stats['added']} added, {stats['updated']} updated")
        return stats

    async def get_quarantined_sites(
        self,
        status: str | None = None,
        min_failures: int = 0,
    ) -> list[QuarantineSite]:
        """
        Retorna sites em quarentena.

        Args:
            status: Filtrar por status (quarantined, investigating, resolved)
            min_failures: Minimo de falhas consecutivas

        Returns:
            Lista de sites em quarentena
        """

        def query_quarantine() -> list[QuarantineSite]:
            quarantine = self._quarantine_table()

            query = quarantine.filter(quarantine.consecutive_failures >= min_failures)

            if status:
                query = query.filter(quarantine.status == status)

            result = (
                query.select(
                    "url", "first_failure", "last_failure",
                    "consecutive_failures", "last_error_message",
                    "status", "notes", "created_at"
                )
                .order_by(ibis.desc("consecutive_failures"), ibis.desc("last_failure"))
                .to_pandas()
            )

            return [
                QuarantineSite(
                    url=row["url"],
                    first_failure=row["first_failure"].isoformat() if row["first_failure"] else None,
                    last_failure=row["last_failure"].isoformat() if row["last_failure"] else None,
                    consecutive_failures=int(row["consecutive_failures"]),
                    last_error=row["last_error_message"],
                    status=row["status"],
                    notes=row["notes"],
                    created_at=row["created_at"].isoformat() if row["created_at"] else None,
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
            result = self.con.raw_sql("""
                UPDATE quarantine
                SET status = $1, notes = $2, updated_at = CURRENT_TIMESTAMP
                WHERE url = $3
                RETURNING id
            """, parameters=[status, notes, url]).fetchone()

            if result:
                logger.info(f"Quarantine status updated: {url} -> {status}")
                return True
            return False

        return await asyncio.to_thread(update_status)

    async def remove_from_quarantine(self, url: str) -> bool:
        """Remove um site da quarentena."""

        def remove() -> bool:
            result = self.con.raw_sql(
                "DELETE FROM quarantine WHERE url = $1 RETURNING id",
                parameters=[url]
            ).fetchone()

            if result:
                logger.info(f"Removed from quarantine: {url}")
                return True
            return False

        return await asyncio.to_thread(remove)

    async def get_quarantine_stats(self) -> QuarantineStats:
        """Retorna estatisticas da quarentena."""

        def query_stats() -> QuarantineStats:
            quarantine = self._quarantine_table()

            result = quarantine.aggregate(
                total=quarantine.count(),
                quarantined=(quarantine.status == "quarantined").sum(),
                investigating=(quarantine.status == "investigating").sum(),
                resolved=(quarantine.status == "resolved").sum(),
                wrong_url=(quarantine.status == "wrong_url").sum(),
                avg_failures=quarantine.consecutive_failures.mean(),
                max_failures=quarantine.consecutive_failures.max(),
            ).to_pandas()

            row = result.iloc[0] if not result.empty else {}

            return QuarantineStats(
                total=int(row.get("total", 0) or 0),
                quarantined=int(row.get("quarantined", 0) or 0),
                investigating=int(row.get("investigating", 0) or 0),
                resolved=int(row.get("resolved", 0) or 0),
                wrong_url=int(row.get("wrong_url", 0) or 0),
                avg_failures=round(row.get("avg_failures", 0) or 0, 1),
                max_failures=int(row.get("max_failures", 0) or 0),
            )

        return await asyncio.to_thread(query_stats)

    async def get_urls_to_skip_quarantine(self) -> set[str]:
        """Retorna URLs em quarentena que devem ser puladas na coleta."""

        def query_urls() -> set[str]:
            quarantine = self._quarantine_table()

            result = (
                quarantine.filter(quarantine.status.isin(["quarantined", "wrong_url"]))
                .select("url")
                .to_pandas()
            )

            return set(result["url"].tolist())

        return await asyncio.to_thread(query_urls)

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
        quarantine_file = await self._export_quarantine_dashboard(output_dir, generated_at)
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
            summaries = self._summaries_table()

            # Get latest audit per URL
            with_rn = summaries.filter(~summaries.has_errors).mutate(
                rn=ibis.row_number().over(
                    ibis.window(group_by="url", order_by=ibis.desc("timestamp"))
                )
            )
            latest = (
                with_rn.filter(with_rn.rn == 0)
                .select(
                    "url", "timestamp",
                    "mobile_accessibility", "mobile_performance",
                    "mobile_seo", "mobile_best_practices",
                    "desktop_accessibility", "desktop_performance",
                    "mobile_fcp", "mobile_lcp", "mobile_cls"
                )
            )

            # Add rank
            ranked = (
                latest.mutate(
                    rank=ibis.rank().over(
                        ibis.window(order_by=ibis.desc("mobile_accessibility"))
                    ) + 1
                )
                .order_by(ibis.desc("mobile_accessibility"))
                .to_pandas()
            )

            return [
                {
                    "url": row["url"],
                    "name": self._extract_name_from_url(row["url"]),
                    "state": self._extract_state_from_url(row["url"]),
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "score": round((row["mobile_accessibility"] or 0) * 100, 1),
                    "performance": round((row["mobile_performance"] or 0) * 100, 1),
                    "seo": round((row["mobile_seo"] or 0) * 100, 1),
                    "best_practices": round((row["mobile_best_practices"] or 0) * 100, 1),
                    "desktop_accessibility": round((row["desktop_accessibility"] or 0) * 100, 1) if row["desktop_accessibility"] else None,
                    "desktop_performance": round((row["desktop_performance"] or 0) * 100, 1) if row["desktop_performance"] else None,
                    "fcp": row["mobile_fcp"],
                    "lcp": row["mobile_lcp"],
                    "cls": row["mobile_cls"],
                    "rank": int(row["rank"]),
                }
                for _, row in ranked.iterrows()
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
                    f, indent=2, ensure_ascii=False
                )
            with open(worst50_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"generated_at": generated_at, "sites": worst50},
                    f, indent=2, ensure_ascii=False
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
                    f, indent=2, ensure_ascii=False
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
                json.dump({
                    "generated_at": generated_at,
                    "stats": quarantine_stats,
                    "sites": quarantine,
                }, f, indent=2, ensure_ascii=False)

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
        if self.con:
            self.con.disconnect()
            self.con = None
