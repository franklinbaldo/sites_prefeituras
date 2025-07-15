"""Modelos Pydantic para dados do PageSpeed Insights."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl


class LighthouseMetric(BaseModel):
    """Métrica individual do Lighthouse."""
    id: str
    title: str
    description: str
    score: Optional[float] = None
    displayValue: Optional[str] = None
    numericValue: Optional[float] = None
    numericUnit: Optional[str] = None


class LighthouseCategory(BaseModel):
    """Categoria do Lighthouse (Performance, Accessibility, etc.)."""
    id: str
    title: str
    description: str
    score: Optional[float] = None
    manualDescription: Optional[str] = None


class LighthouseAudit(BaseModel):
    """Auditoria individual do Lighthouse."""
    id: str
    title: str
    description: str
    score: Optional[Union[float, int]] = None
    scoreDisplayMode: Optional[str] = None
    displayValue: Optional[str] = None
    explanation: Optional[str] = None
    errorMessage: Optional[str] = None
    warnings: Optional[List[str]] = None
    details: Optional[Dict] = None


class LighthouseResult(BaseModel):
    """Resultado completo do Lighthouse."""
    requestedUrl: HttpUrl
    finalUrl: HttpUrl
    lighthouseVersion: str
    userAgent: str
    fetchTime: str
    environment: Dict
    runWarnings: List[str] = Field(default_factory=list)
    configSettings: Dict
    categories: Dict[str, LighthouseCategory]
    audits: Dict[str, LighthouseAudit]


class PageSpeedInsightsResult(BaseModel):
    """Resultado completo da API PageSpeed Insights."""
    captchaResult: Optional[str] = None
    kind: str = "pagespeedonline#result"
    id: HttpUrl
    loadingExperience: Optional[Dict] = None
    originLoadingExperience: Optional[Dict] = None
    lighthouseResult: LighthouseResult
    analysisUTCTimestamp: str
    version: Dict[str, str]


class SiteAudit(BaseModel):
    """Auditoria completa de um site (mobile + desktop)."""
    url: HttpUrl
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mobile_result: Optional[PageSpeedInsightsResult] = None
    desktop_result: Optional[PageSpeedInsightsResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AuditSummary(BaseModel):
    """Resumo das métricas principais de uma auditoria."""
    url: HttpUrl
    timestamp: datetime
    
    # Scores principais (0-1)
    mobile_performance: Optional[float] = None
    mobile_accessibility: Optional[float] = None
    mobile_best_practices: Optional[float] = None
    mobile_seo: Optional[float] = None
    
    desktop_performance: Optional[float] = None
    desktop_accessibility: Optional[float] = None
    desktop_best_practices: Optional[float] = None
    desktop_seo: Optional[float] = None
    
    # Core Web Vitals
    mobile_fcp: Optional[float] = None  # First Contentful Paint
    mobile_lcp: Optional[float] = None  # Largest Contentful Paint
    mobile_cls: Optional[float] = None  # Cumulative Layout Shift
    mobile_fid: Optional[float] = None  # First Input Delay
    
    desktop_fcp: Optional[float] = None
    desktop_lcp: Optional[float] = None
    desktop_cls: Optional[float] = None
    desktop_fid: Optional[float] = None
    
    # Status
    has_errors: bool = False
    error_message: Optional[str] = None


class BatchAuditConfig(BaseModel):
    """Configuração para auditoria em lote."""
    csv_file: str
    output_dir: str = "./output"
    max_concurrent: int = 5
    requests_per_second: float = 1.0
    retry_attempts: int = 3
    retry_delay: float = 2.0
    strategies: List[str] = Field(default=["mobile", "desktop"])
    
    # Filtros
    url_column: str = "url"
    skip_existing: bool = True
    
    # Export
    export_parquet: bool = True
    export_json: bool = True
    upload_to_ia: bool = False