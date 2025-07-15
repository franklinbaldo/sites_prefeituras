"""Sistema de armazenamento com DuckDB - substitui a lógica Node.js."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import duckdb
import pandas as pd
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
    
    async def get_latest_summaries(self, limit: int = 100) -> List[AuditSummary]:
        """Obtém resumos mais recentes."""
        results = self.conn.execute("""
            SELECT * FROM audit_summaries 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, [limit]).fetchall()
        
        # Converter para objetos Pydantic
        summaries = []
        for row in results:
            # TODO: Implementar conversão completa
            pass
        
        return summaries
    
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
        
        console.print(f"✅ Dados exportados para {output_dir}")
    
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
        
        console.print(f"✅ JSON exportado para {json_file}")
    
    async def close(self) -> None:
        """Fecha conexão com banco."""
        if self.conn:
            self.conn.close()
            self.conn = None