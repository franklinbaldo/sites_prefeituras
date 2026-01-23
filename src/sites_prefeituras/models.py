"""Modelos Pydantic para dados do PageSpeed Insights."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LighthouseMetric(BaseModel):
    """Métrica individual do Lighthouse."""

    id: str
    title: str
    description: str
    score: float | None = None
    displayValue: str | None = None
    numericValue: float | None = None
    numericUnit: str | None = None


class LighthouseCategory(BaseModel):
    """Categoria do Lighthouse (Performance, Accessibility, etc.)."""

    id: str
    title: str
    description: str
    score: float | None = None
    manualDescription: str | None = None


class LighthouseAudit(BaseModel):
    """Auditoria individual do Lighthouse."""

    id: str
    title: str
    description: str
    score: float | int | None = None
    scoreDisplayMode: str | None = None
    displayValue: str | None = None
    numericValue: float | None = None
    explanation: str | None = None
    errorMessage: str | None = None
    warnings: list[str] | None = None
    details: dict[str, Any] | None = None


class LighthouseResult(BaseModel):
    """Resultado completo do Lighthouse."""

    requestedUrl: HttpUrl
    finalUrl: HttpUrl
    lighthouseVersion: str
    userAgent: str
    fetchTime: str
    environment: dict[str, Any]
    runWarnings: list[str] = Field(default_factory=list)
    configSettings: dict[str, Any]
    categories: dict[str, LighthouseCategory]
    audits: dict[str, LighthouseAudit]


class PageSpeedInsightsResult(BaseModel):
    """Resultado completo da API PageSpeed Insights."""

    captchaResult: str | None = None
    kind: str = "pagespeedonline#result"
    id: HttpUrl
    loadingExperience: dict[str, Any] | None = None
    originLoadingExperience: dict[str, Any] | None = None
    lighthouseResult: LighthouseResult
    analysisUTCTimestamp: str
    version: dict[str, str]


class SiteAudit(BaseModel):
    """Auditoria completa de um site (mobile + desktop)."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    url: HttpUrl
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mobile_result: PageSpeedInsightsResult | None = None
    desktop_result: PageSpeedInsightsResult | None = None
    error_message: str | None = None
    retry_count: int = 0


class AuditSummary(BaseModel):
    """Resumo das métricas principais de uma auditoria."""

    url: HttpUrl
    timestamp: datetime

    # Scores principais (0-1)
    mobile_performance: float | None = None
    mobile_accessibility: float | None = None
    mobile_best_practices: float | None = None
    mobile_seo: float | None = None

    desktop_performance: float | None = None
    desktop_accessibility: float | None = None
    desktop_best_practices: float | None = None
    desktop_seo: float | None = None

    # Core Web Vitals
    mobile_fcp: float | None = None  # First Contentful Paint
    mobile_lcp: float | None = None  # Largest Contentful Paint
    mobile_cls: float | None = None  # Cumulative Layout Shift
    mobile_fid: float | None = None  # First Input Delay

    desktop_fcp: float | None = None
    desktop_lcp: float | None = None
    desktop_cls: float | None = None
    desktop_fid: float | None = None

    # Status
    has_errors: bool = False
    error_message: str | None = None


class BatchAuditConfig(BaseModel):
    """Configuração para auditoria em lote."""

    csv_file: str
    output_dir: str = "./output"
    max_concurrent: int = 10
    requests_per_second: float = 3.5
    retry_attempts: int = 3
    retry_delay: float = 2.0
    strategies: list[str] = Field(default=["mobile", "desktop"])

    # Filtros
    url_column: str = "url"
    skip_existing: bool = True
    skip_recent_hours: int = (
        24  # Pular sites auditados nas ultimas N horas (0 = desativado)
    )

    # Export
    export_parquet: bool = True
    export_json: bool = True
