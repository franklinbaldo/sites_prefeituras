"""Fixtures compartilhadas para testes BDD."""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import ibis
import pytest
import pytest_asyncio
import respx

from sites_prefeituras.storage import DuckDBStorage

# ============================================================================
# Fixtures de banco de dados (Ibis)
# ============================================================================


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Cria caminho para banco de dados temporario para testes."""
    # DuckDB needs either a non-existent path or a valid DB file
    # Don't create the file - just generate a unique path
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.duckdb"
        yield str(db_path)
        # Cleanup happens when TemporaryDirectory context exits


@pytest_asyncio.fixture
async def storage(temp_db_path: str) -> AsyncGenerator[DuckDBStorage, None]:
    """Storage inicializado para testes (async)."""
    db = DuckDBStorage(temp_db_path)
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def storage_sync(temp_db_path: str) -> Generator[DuckDBStorage, None, None]:
    """Storage inicializado para testes BDD (sync wrapper).

    The storage uses Ibis with DuckDB backend.
    Use storage_sync.con.raw_sql() for direct SQL execution in tests.
    """
    db = DuckDBStorage(temp_db_path)
    asyncio.run(db.initialize())
    yield db
    asyncio.run(db.close())


# Helper for backward compatibility - allows conn.execute() pattern
class IbisConnectionWrapper:
    """Wrapper to provide conn.execute() interface for Ibis backend."""

    def __init__(self, ibis_con: ibis.BaseBackend):
        self._con = ibis_con

    def execute(self, query: str, params: list | None = None) -> None:
        """Execute SQL with optional parameters (for backward compatibility)."""
        if params:
            # Ibis raw_sql doesn't support parameterized queries directly
            # We need to format the query safely
            # This is a simplified approach for tests only
            formatted_query = query
            for param in params:
                if param is None:
                    formatted_query = formatted_query.replace("?", "NULL", 1)
                elif isinstance(param, str):
                    # Escape single quotes
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


# ============================================================================
# Fixtures de mock da API PSI
# ============================================================================


def create_psi_response(
    url: str,
    performance: float = 0.75,
    accessibility: float = 0.80,
    seo: float = 0.85,
    best_practices: float = 0.90,
    fcp: float = 2000,
    lcp: float = 3000,
    cls: float = 0.1,
) -> dict:
    """Cria resposta mockada da API PSI."""
    return {
        "captchaResult": "CAPTCHA_NOT_NEEDED",
        "kind": "pagespeedonline#result",
        "id": url,
        "loadingExperience": {},
        "originLoadingExperience": {},
        "analysisUTCTimestamp": "2025-01-22T12:00:00.000Z",
        "version": {"major": "9", "minor": "0"},
        "lighthouseResult": {
            "requestedUrl": url,
            "finalUrl": url,
            "lighthouseVersion": "11.0.0",
            "userAgent": "Mozilla/5.0",
            "fetchTime": "2025-01-22T12:00:00.000Z",
            "environment": {"networkUserAgent": "Mozilla/5.0"},
            "runWarnings": [],
            "configSettings": {"emulatedFormFactor": "mobile"},
            "categories": {
                "performance": {
                    "id": "performance",
                    "title": "Performance",
                    "description": "Performance score",
                    "score": performance,
                },
                "accessibility": {
                    "id": "accessibility",
                    "title": "Accessibility",
                    "description": "Accessibility score",
                    "score": accessibility,
                },
                "seo": {
                    "id": "seo",
                    "title": "SEO",
                    "description": "SEO score",
                    "score": seo,
                },
                "best-practices": {
                    "id": "best-practices",
                    "title": "Best Practices",
                    "description": "Best practices score",
                    "score": best_practices,
                },
            },
            "audits": {
                "first-contentful-paint": {
                    "id": "first-contentful-paint",
                    "title": "First Contentful Paint",
                    "description": "FCP",
                    "score": 0.8,
                    "numericValue": fcp,
                    "numericUnit": "millisecond",
                },
                "largest-contentful-paint": {
                    "id": "largest-contentful-paint",
                    "title": "Largest Contentful Paint",
                    "description": "LCP",
                    "score": 0.7,
                    "numericValue": lcp,
                    "numericUnit": "millisecond",
                },
                "cumulative-layout-shift": {
                    "id": "cumulative-layout-shift",
                    "title": "Cumulative Layout Shift",
                    "description": "CLS",
                    "score": 0.9,
                    "numericValue": cls,
                    "numericUnit": "unitless",
                },
                "max-potential-fid": {
                    "id": "max-potential-fid",
                    "title": "Max Potential FID",
                    "description": "FID",
                    "score": 0.85,
                    "numericValue": 150,
                    "numericUnit": "millisecond",
                },
            },
        },
    }


@pytest.fixture
def mock_psi_api():
    """Mock da API PSI usando respx."""
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock


@pytest.fixture
def psi_success_response():
    """Resposta de sucesso padrao."""
    return create_psi_response


@pytest.fixture
def psi_error_response():
    """Resposta de erro."""
    return {"error": {"code": 500, "message": "Internal Server Error"}}


# ============================================================================
# Fixtures de URLs de teste
# ============================================================================


@pytest.fixture
def sample_urls() -> list[str]:
    """Lista de URLs de exemplo."""
    return [
        "https://www.prefeitura1.gov.br",
        "https://www.prefeitura2.gov.br",
        "https://www.prefeitura3.gov.br",
        "https://www.prefeitura4.gov.br",
        "https://www.prefeitura5.gov.br",
    ]


@pytest.fixture
def sample_csv(tmp_path: Path, sample_urls: list[str]) -> Path:
    """Cria CSV de exemplo para testes."""
    csv_file = tmp_path / "test_sites.csv"
    csv_file.write_text("url\n" + "\n".join(sample_urls))
    return csv_file


# ============================================================================
# Fixtures de configuracao
# ============================================================================


@pytest.fixture
def api_key() -> str:
    """API key fake para testes."""
    return "TEST_API_KEY_12345"


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Diretorio de saida temporario."""
    out = tmp_path / "output"
    out.mkdir()
    return out
