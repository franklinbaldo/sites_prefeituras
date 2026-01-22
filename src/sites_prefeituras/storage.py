"""Sistema de armazenamento com DuckDB - substitui a lógica Node.js."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import duckdb
from rich.console import Console

from .models import SiteAudit, AuditSummary

logger = logging.getLogger(__name__)
console = Console()


class DuckDBStorage:
    """Sistema de armazenamento usando DuckDB."""
    
    def __init__(self, db_path: str = "./data/sites_prefeituras.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        
    async def initialize(self) -> None:
        """Inicializa o banco de dados e cria tabelas."""
        self.conn = duckdb.connect(str(self.db_path))
        await self._create_tables()
        
    async def _create_tables(self) -> None:
        """Cria tabelas necessárias."""
        # Tabela principal de auditorias
        self.conn.execute("""
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
        
        # Tabela de resumos (para consultas rápidas)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_summaries (
                id INTEGER PRIMARY KEY,
                url VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                
                -- Scores principais (0-1)
                mobile_performance DOUBLE,
                mobile_accessibility DOUBLE,
                mobile_best_practices DOUBLE,
                mobile_seo DOUBLE,
                
                desktop_performance DOUBLE,
                desktop_accessibility DOUBLE,
                desktop_best_practices DOUBLE,
                desktop_seo DOUBLE,
                
                -- Core Web Vitals
                mobile_fcp DOUBLE,
                mobile_lcp DOUBLE,
                mobile_cls DOUBLE,
                mobile_fid DOUBLE,
                
                desktop_fcp DOUBLE,
                desktop_lcp DOUBLE,
                desktop_cls DOUBLE,
                desktop_fid DOUBLE,
                
                -- Status
                has_errors BOOLEAN DEFAULT FALSE,
                error_message VARCHAR,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_timestamp ON audits(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_url ON audit_summaries(url)")

        # Tabela de quarentena (sites com falhas persistentes)
        self.conn.execute("""
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
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_url ON quarantine(url)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine(status)")

        logger.info("Database tables initialized")
    
    async def save_audit(self, audit: SiteAudit) -> int:
        """Salva uma auditoria completa."""
        # Inserir auditoria completa
        audit_id = self.conn.execute("""
            INSERT INTO audits (url, timestamp, mobile_result, desktop_result, error_message, retry_count)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        """, [
            str(audit.url),
            audit.timestamp,
            audit.mobile_result.model_dump_json() if audit.mobile_result else None,
            audit.desktop_result.model_dump_json() if audit.desktop_result else None,
            audit.error_message,
            audit.retry_count,
        ]).fetchone()[0]
        
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
            categories = audit.mobile_result.lighthouseResult.categories
            summary.mobile_performance = categories.get("performance", {}).score
            summary.mobile_accessibility = categories.get("accessibility", {}).score
            summary.mobile_best_practices = categories.get("best-practices", {}).score
            summary.mobile_seo = categories.get("seo", {}).score
            
            # Core Web Vitals mobile
            audits = audit.mobile_result.lighthouseResult.audits
            summary.mobile_fcp = self._extract_metric_value(audits.get("first-contentful-paint"))
            summary.mobile_lcp = self._extract_metric_value(audits.get("largest-contentful-paint"))
            summary.mobile_cls = self._extract_metric_value(audits.get("cumulative-layout-shift"))
            summary.mobile_fid = self._extract_metric_value(audits.get("max-potential-fid"))
        
        # Extrair scores desktop
        if audit.desktop_result:
            categories = audit.desktop_result.lighthouseResult.categories
            summary.desktop_performance = categories.get("performance", {}).score
            summary.desktop_accessibility = categories.get("accessibility", {}).score
            summary.desktop_best_practices = categories.get("best-practices", {}).score
            summary.desktop_seo = categories.get("seo", {}).score
            
            # Core Web Vitals desktop
            audits = audit.desktop_result.lighthouseResult.audits
            summary.desktop_fcp = self._extract_metric_value(audits.get("first-contentful-paint"))
            summary.desktop_lcp = self._extract_metric_value(audits.get("largest-contentful-paint"))
            summary.desktop_cls = self._extract_metric_value(audits.get("cumulative-layout-shift"))
            summary.desktop_fid = self._extract_metric_value(audits.get("max-potential-fid"))
        
        return summary
    
    def _extract_metric_value(self, audit_data) -> Optional[float]:
        """Extrai valor numérico de uma métrica."""
        if audit_data and hasattr(audit_data, 'numericValue'):
            return audit_data.numericValue
        return None
    
    async def _save_summary(self, summary: AuditSummary) -> None:
        """Salva resumo da auditoria."""
        self.conn.execute("""
            INSERT INTO audit_summaries (
                url, timestamp,
                mobile_performance, mobile_accessibility, mobile_best_practices, mobile_seo,
                desktop_performance, desktop_accessibility, desktop_best_practices, desktop_seo,
                mobile_fcp, mobile_lcp, mobile_cls, mobile_fid,
                desktop_fcp, desktop_lcp, desktop_cls, desktop_fid,
                has_errors, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(summary.url), summary.timestamp,
            summary.mobile_performance, summary.mobile_accessibility, 
            summary.mobile_best_practices, summary.mobile_seo,
            summary.desktop_performance, summary.desktop_accessibility,
            summary.desktop_best_practices, summary.desktop_seo,
            summary.mobile_fcp, summary.mobile_lcp, summary.mobile_cls, summary.mobile_fid,
            summary.desktop_fcp, summary.desktop_lcp, summary.desktop_cls, summary.desktop_fid,
            summary.has_errors, summary.error_message,
        ])
    
    async def get_recently_audited_urls(self, hours: int = 24) -> set[str]:
        """Retorna URLs auditadas nas ultimas N horas (para coleta incremental)."""
        results = self.conn.execute("""
            SELECT DISTINCT url
            FROM audits
            WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL ? HOUR
              AND error_message IS NULL
        """, [hours]).fetchall()

        urls = {row[0] for row in results}
        logger.info(f"Found {len(urls)} URLs audited in last {hours} hours")
        return urls

    async def export_to_parquet(self, output_dir: Path) -> None:
        """Exporta dados para arquivos Parquet particionados."""
        output_dir.mkdir(exist_ok=True)
        
        # Export auditorias completas
        audits_df = self.conn.execute("""
            SELECT 
                url, timestamp, error_message, retry_count,
                DATE_TRUNC('day', timestamp) as date_partition
            FROM audits
        """).df()
        
        if not audits_df.empty:
            # Particionar por data
            for date, group in audits_df.groupby('date_partition'):
                date_str = date.strftime('%Y-%m-%d')
                parquet_file = output_dir / f"audits_date={date_str}.parquet"
                group.drop('date_partition', axis=1).to_parquet(parquet_file)
        
        # Export resumos
        summaries_df = self.conn.execute("SELECT * FROM audit_summaries").df()
        if not summaries_df.empty:
            summaries_file = output_dir / "audit_summaries.parquet"
            summaries_df.to_parquet(summaries_file)
        
        console.print(f"Dados exportados para {output_dir}")

    async def export_to_json(self, output_dir: Path) -> None:
        """Exporta dados para JSON (para visualização web)."""
        output_dir.mkdir(exist_ok=True)
        
        # Export resumo para visualização
        summaries = self.conn.execute("""
            SELECT 
                url, timestamp,
                mobile_performance, desktop_performance,
                mobile_accessibility, desktop_accessibility,
                has_errors, error_message
            FROM audit_summaries
            ORDER BY timestamp DESC
            LIMIT 1000
        """).fetchall()
        
        # Converter para formato JSON amigável
        json_data = {
            "last_updated": datetime.utcnow().isoformat(),
            "total_sites": len(summaries),
            "audits": [
                {
                    "url": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "mobile_performance": row[2],
                    "desktop_performance": row[3],
                    "mobile_accessibility": row[4],
                    "desktop_accessibility": row[5],
                    "has_errors": row[6],
                    "error_message": row[7],
                }
                for row in summaries
            ]
        }
        
        json_file = output_dir / "latest_audits.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"JSON exportado para {json_file}")

    # ========================================================================
    # Metricas agregadas
    # ========================================================================

    async def get_aggregated_metrics(self) -> dict:
        """Retorna metricas agregadas de todas as auditorias."""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total_audits,
                COUNT(*) FILTER (WHERE NOT has_errors) as successful_audits,
                COUNT(*) FILTER (WHERE has_errors) as failed_audits,
                AVG(mobile_performance) as avg_mobile_performance,
                AVG(desktop_performance) as avg_desktop_performance,
                AVG(mobile_accessibility) as avg_mobile_accessibility,
                AVG(desktop_accessibility) as avg_desktop_accessibility,
                AVG(mobile_seo) as avg_mobile_seo,
                AVG(desktop_seo) as avg_desktop_seo,
                AVG(mobile_best_practices) as avg_mobile_best_practices,
                AVG(desktop_best_practices) as avg_desktop_best_practices,
                STDDEV(mobile_performance) as std_mobile_performance,
                STDDEV(desktop_performance) as std_desktop_performance,
                MIN(mobile_performance) as min_mobile_performance,
                MAX(mobile_performance) as max_mobile_performance
            FROM audit_summaries
        """).fetchone()

        total = result[0] or 0
        successful = result[1] or 0

        return {
            "total_audits": total,
            "successful_audits": successful,
            "failed_audits": result[2] or 0,
            "success_rate": successful / total if total > 0 else 0,
            "error_rate": (result[2] or 0) / total if total > 0 else 0,
            "avg_mobile_performance": result[3],
            "avg_desktop_performance": result[4],
            "avg_mobile_accessibility": result[5],
            "avg_desktop_accessibility": result[6],
            "avg_mobile_seo": result[7],
            "avg_desktop_seo": result[8],
            "avg_mobile_best_practices": result[9],
            "avg_desktop_best_practices": result[10],
            "std_mobile_performance": result[11],
            "std_desktop_performance": result[12],
            "min_mobile_performance": result[13],
            "max_mobile_performance": result[14],
        }

    async def get_metrics_by_state(self) -> list[dict]:
        """Retorna metricas agregadas por estado (extraido da URL)."""
        # Extrai estado do dominio (ex: prefeitura.sp.gov.br -> SP)
        results = self.conn.execute("""
            WITH state_extract AS (
                SELECT
                    url,
                    UPPER(REGEXP_EXTRACT(url, '\.([a-z]{2})\.gov\.br', 1)) as state,
                    mobile_performance,
                    desktop_performance,
                    mobile_accessibility,
                    desktop_accessibility
                FROM audit_summaries
                WHERE NOT has_errors
            )
            SELECT
                state,
                COUNT(*) as site_count,
                AVG(mobile_performance) as avg_performance,
                AVG(mobile_accessibility) as avg_accessibility
            FROM state_extract
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            ORDER BY avg_performance DESC
        """).fetchall()

        return [
            {
                "state": row[0],
                "site_count": row[1],
                "avg_performance": row[2],
                "avg_accessibility": row[3],
            }
            for row in results
        ]

    async def get_worst_performing_sites(self, limit: int = 10) -> list[dict]:
        """Retorna os sites com pior performance."""
        results = self.conn.execute("""
            SELECT
                url,
                mobile_performance,
                desktop_performance,
                mobile_accessibility,
                timestamp
            FROM audit_summaries
            WHERE NOT has_errors AND mobile_performance IS NOT NULL
            ORDER BY mobile_performance ASC
            LIMIT ?
        """, [limit]).fetchall()

        return [
            {
                "url": row[0],
                "mobile_performance": row[1],
                "desktop_performance": row[2],
                "mobile_accessibility": row[3],
                "timestamp": row[4].isoformat() if row[4] else None,
            }
            for row in results
        ]

    async def get_best_accessibility_sites(self, limit: int = 10) -> list[dict]:
        """Retorna os sites com melhor acessibilidade."""
        results = self.conn.execute("""
            SELECT
                url,
                mobile_accessibility,
                desktop_accessibility,
                mobile_performance,
                timestamp
            FROM audit_summaries
            WHERE NOT has_errors AND mobile_accessibility IS NOT NULL
            ORDER BY mobile_accessibility DESC
            LIMIT ?
        """, [limit]).fetchall()

        return [
            {
                "url": row[0],
                "mobile_accessibility": row[1],
                "desktop_accessibility": row[2],
                "mobile_performance": row[3],
                "timestamp": row[4].isoformat() if row[4] else None,
            }
            for row in results
        ]

    async def get_temporal_evolution(self, url: str) -> list[dict]:
        """Retorna evolucao temporal de metricas para uma URL."""
        results = self.conn.execute("""
            SELECT
                timestamp,
                mobile_performance,
                desktop_performance,
                mobile_accessibility,
                desktop_accessibility
            FROM audit_summaries
            WHERE url = ? AND NOT has_errors
            ORDER BY timestamp ASC
        """, [url]).fetchall()

        return [
            {
                "timestamp": row[0].isoformat() if row[0] else None,
                "mobile_performance": row[1],
                "desktop_performance": row[2],
                "mobile_accessibility": row[3],
                "desktop_accessibility": row[4],
            }
            for row in results
        ]

    async def export_aggregated_metrics_json(self, output_file: Path) -> None:
        """Exporta metricas agregadas para JSON."""
        metrics = await self.get_aggregated_metrics()
        metrics["generated_at"] = datetime.utcnow().isoformat()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        logger.info(f"Aggregated metrics exported to {output_file}")

    # ========================================================================
    # Sistema de Quarentena
    # ========================================================================

    async def update_quarantine(self, min_consecutive_days: int = 3) -> dict:
        """
        Atualiza a lista de quarentena baseado em falhas consecutivas.

        Sites que falharam por N dias consecutivos sao adicionados a quarentena.
        Isso ajuda a identificar URLs que podem ter mudado ou estao incorretas.

        Args:
            min_consecutive_days: Minimo de dias com falha para entrar em quarentena

        Returns:
            Estatisticas da atualizacao
        """
        # Encontrar sites com falhas consecutivas nos ultimos N dias
        results = self.conn.execute("""
            WITH daily_failures AS (
                SELECT
                    url,
                    DATE(timestamp) as failure_date,
                    error_message,
                    ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) as rn
                FROM audits
                WHERE error_message IS NOT NULL
            ),
            consecutive_failures AS (
                SELECT
                    url,
                    MIN(failure_date) as first_failure,
                    MAX(failure_date) as last_failure,
                    COUNT(DISTINCT failure_date) as failure_days,
                    MAX(CASE WHEN rn = 1 THEN error_message END) as last_error
                FROM daily_failures
                WHERE failure_date >= CURRENT_DATE - INTERVAL ? DAY
                GROUP BY url
                HAVING COUNT(DISTINCT failure_date) >= ?
            )
            SELECT url, first_failure, last_failure, failure_days, last_error
            FROM consecutive_failures
        """, [min_consecutive_days * 2, min_consecutive_days]).fetchall()

        added = 0
        updated = 0

        for url, first_failure, last_failure, failure_days, last_error in results:
            # Verificar se ja existe na quarentena
            existing = self.conn.execute(
                "SELECT id, consecutive_failures FROM quarantine WHERE url = ?",
                [url]
            ).fetchone()

            if existing:
                # Atualizar registro existente
                self.conn.execute("""
                    UPDATE quarantine
                    SET last_failure = ?,
                        consecutive_failures = ?,
                        last_error_message = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """, [last_failure, failure_days, last_error, url])
                updated += 1
            else:
                # Adicionar novo registro
                self.conn.execute("""
                    INSERT INTO quarantine (url, first_failure, last_failure,
                                           consecutive_failures, last_error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, [url, first_failure, last_failure, failure_days, last_error])
                added += 1

        logger.info(f"Quarantine updated: {added} added, {updated} updated")
        return {"added": added, "updated": updated, "total_checked": len(results)}

    async def get_quarantined_sites(
        self,
        status: Optional[str] = None,
        min_failures: int = 0
    ) -> list[dict]:
        """
        Retorna sites em quarentena.

        Args:
            status: Filtrar por status (quarantined, investigating, resolved)
            min_failures: Minimo de falhas consecutivas

        Returns:
            Lista de sites em quarentena
        """
        query = """
            SELECT
                url,
                first_failure,
                last_failure,
                consecutive_failures,
                last_error_message,
                status,
                notes,
                created_at
            FROM quarantine
            WHERE consecutive_failures >= ?
        """
        params = [min_failures]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY consecutive_failures DESC, last_failure DESC"

        results = self.conn.execute(query, params).fetchall()

        return [
            {
                "url": row[0],
                "first_failure": row[1].isoformat() if row[1] else None,
                "last_failure": row[2].isoformat() if row[2] else None,
                "consecutive_failures": row[3],
                "last_error": row[4],
                "status": row[5],
                "notes": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
            }
            for row in results
        ]

    async def update_quarantine_status(
        self,
        url: str,
        status: str,
        notes: Optional[str] = None
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

        result = self.conn.execute("""
            UPDATE quarantine
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE url = ?
            RETURNING id
        """, [status, notes, url]).fetchone()

        if result:
            logger.info(f"Quarantine status updated: {url} -> {status}")
            return True
        return False

    async def remove_from_quarantine(self, url: str) -> bool:
        """Remove um site da quarentena."""
        result = self.conn.execute(
            "DELETE FROM quarantine WHERE url = ? RETURNING id",
            [url]
        ).fetchone()

        if result:
            logger.info(f"Removed from quarantine: {url}")
            return True
        return False

    async def get_quarantine_stats(self) -> dict:
        """Retorna estatisticas da quarentena."""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'quarantined') as quarantined,
                COUNT(*) FILTER (WHERE status = 'investigating') as investigating,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
                COUNT(*) FILTER (WHERE status = 'wrong_url') as wrong_url,
                AVG(consecutive_failures) as avg_failures,
                MAX(consecutive_failures) as max_failures
            FROM quarantine
        """).fetchone()

        return {
            "total": result[0] or 0,
            "quarantined": result[1] or 0,
            "investigating": result[2] or 0,
            "resolved": result[3] or 0,
            "wrong_url": result[4] or 0,
            "avg_failures": round(result[5], 1) if result[5] else 0,
            "max_failures": result[6] or 0,
        }

    async def get_urls_to_skip_quarantine(self) -> set[str]:
        """Retorna URLs em quarentena que devem ser puladas na coleta."""
        results = self.conn.execute("""
            SELECT url FROM quarantine
            WHERE status IN ('quarantined', 'wrong_url')
        """).fetchall()

        return {row[0] for row in results}

    async def export_quarantine_json(self, output_file: Path) -> dict:
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
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Quarantine exported to {output_file}: {len(sites)} sites")
        return {"file": str(output_file), "count": len(sites)}

    async def export_quarantine_csv(self, output_file: Path) -> dict:
        """
        Exporta lista de quarentena para CSV.

        Args:
            output_file: Caminho do arquivo de saida

        Returns:
            Estatisticas da exportacao
        """
        import csv

        sites = await self.get_quarantined_sites()

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            if sites:
                writer = csv.DictWriter(f, fieldnames=sites[0].keys())
                writer.writeheader()
                writer.writerows(sites)

        logger.info(f"Quarantine CSV exported to {output_file}: {len(sites)} sites")
        return {"file": str(output_file), "count": len(sites)}

    # ========================================================================
    # Exportacao para Dashboard (JSON estatico - substitui WASM)
    # ========================================================================

    async def export_dashboard_json(self, output_dir: Path) -> dict:
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
        stats = {"generated_at": generated_at, "files": []}

        # 1. Summary - Metricas agregadas
        summary = await self.get_aggregated_metrics()
        summary["generated_at"] = generated_at
        summary_file = output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(summary_file))

        # 2. Ranking completo (ultimas auditorias de cada site)
        ranking_data = self.conn.execute("""
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
        """).fetchall()

        ranking = [
            {
                "url": row[0],
                "name": self._extract_name_from_url(row[0]),
                "state": self._extract_state_from_url(row[0]),
                "timestamp": row[1].isoformat() if row[1] else None,
                "score": round((row[2] or 0) * 100, 1),  # accessibility 0-100
                "performance": round((row[3] or 0) * 100, 1),
                "seo": round((row[4] or 0) * 100, 1),
                "best_practices": round((row[5] or 0) * 100, 1),
                "desktop_accessibility": round((row[6] or 0) * 100, 1) if row[6] else None,
                "desktop_performance": round((row[7] or 0) * 100, 1) if row[7] else None,
                "fcp": row[8],
                "lcp": row[9],
                "cls": row[10],
                "rank": row[11],
            }
            for row in ranking_data
        ]

        ranking_file = output_dir / "ranking.json"
        ranking_output = {
            "generated_at": generated_at,
            "total": len(ranking),
            "sites": ranking,
        }
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump(ranking_output, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(ranking_file))
        stats["total_sites"] = len(ranking)

        # 3. Top 50 e Worst 50
        top50 = ranking[:50]
        worst50 = sorted(ranking, key=lambda x: x["score"])[:50]

        top50_file = output_dir / "top50.json"
        with open(top50_file, 'w', encoding='utf-8') as f:
            json.dump({"generated_at": generated_at, "sites": top50}, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(top50_file))

        worst50_file = output_dir / "worst50.json"
        with open(worst50_file, 'w', encoding='utf-8') as f:
            json.dump({"generated_at": generated_at, "sites": worst50}, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(worst50_file))

        # 4. Por estado
        by_state = await self.get_metrics_by_state()
        by_state_file = output_dir / "by-state.json"
        with open(by_state_file, 'w', encoding='utf-8') as f:
            json.dump({"generated_at": generated_at, "states": by_state}, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(by_state_file))

        # 5. Quarentena
        quarantine = await self.get_quarantined_sites()
        quarantine_stats = await self.get_quarantine_stats()
        quarantine_file = output_dir / "quarantine.json"
        with open(quarantine_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": generated_at,
                "stats": quarantine_stats,
                "sites": quarantine,
            }, f, indent=2, ensure_ascii=False)
        stats["files"].append(str(quarantine_file))

        logger.info(f"Dashboard JSON exported to {output_dir}: {len(stats['files'])} files")
        console.print(f"Dashboard JSON exportado: {output_dir} ({len(ranking)} sites)")

        return stats

    def _extract_name_from_url(self, url: str) -> str:
        """Extrai nome amigavel de uma URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname or url
            # Remove www. e .gov.br
            name = hostname.replace("www.", "")
            # Remove sufixos comuns
            for suffix in [".gov.br", ".org.br", ".com.br"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
            return name
        except Exception:
            return url

    def _extract_state_from_url(self, url: str) -> str:
        """Extrai estado de uma URL .gov.br."""
        import re
        match = re.search(r'\.([a-z]{2})\.gov\.br', url.lower())
        if match:
            return match.group(1).upper()
        return "N/A"

    async def close(self) -> None:
        """Fecha conexao com banco."""
        if self.conn:
            self.conn.close()
            self.conn = None