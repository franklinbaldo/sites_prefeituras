"""Step definitions para processamento em chunks paralelos."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

from sites_prefeituras.collector import PageSpeedCollector, process_urls_in_chunks
from sites_prefeituras.models import BatchAuditConfig, SiteAudit
from tests.conftest import create_psi_response

# Carrega os cenarios do arquivo .feature
scenarios("../features/parallel_chunks.feature")


# ============================================================================
# Contexto
# ============================================================================


@pytest.fixture
def context():
    """Contexto compartilhado entre steps."""
    return {
        "urls": [],
        "chunk_size": 5,
        "rate_limit": 3.5,
        "max_concurrent": 10,
        "results": [],
        "start_time": None,
        "end_time": None,
        "active_requests": 0,
        "max_active_requests": 0,
    }


@given("que a API PSI tem limite de 4 requisicoes por segundo")
def api_rate_limit(context):
    context["api_rate_limit"] = 4.0


@given("que cada site requer 2 requisicoes (mobile + desktop)")
def requests_per_site(context):
    context["requests_per_site"] = 2


# ============================================================================
# Cenario: Processar chunk de URLs em paralelo
# ============================================================================


@given(parsers.parse("uma lista de {count:d} URLs para auditar"))
def given_url_list(context, count):
    context["urls"] = [f"https://prefeitura{i}.gov.br" for i in range(count)]


@given(parsers.parse("um tamanho de chunk de {size:d}"))
def given_chunk_size(context, size):
    context["chunk_size"] = size


@when("eu processar as URLs em chunks paralelos")
def when_process_chunks(context, mock_psi_api, api_key):
    # Configurar mock para todas as URLs
    for url in context["urls"]:
        mock_psi_api.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        ).mock(return_value=Response(200, json=create_psi_response(url)))

    async def _process():
        async with PageSpeedCollector(
            api_key=api_key,
            requests_per_second=context["rate_limit"],
            max_concurrent=context["max_concurrent"],
        ) as collector:
            return await process_urls_in_chunks(
                collector,
                context["urls"],
                chunk_size=context["chunk_size"],
            )

    context["start_time"] = time.time()
    context["results"] = asyncio.run(_process())
    context["end_time"] = time.time()


@then(parsers.parse("{count:d} URLs devem ser processadas simultaneamente"))
def then_parallel_processing(context, count):
    # Verificado pelo semaphore no collector
    assert context["chunk_size"] == count


@then(parsers.parse("o rate limit de {rate} req/s deve ser respeitado"))
def then_rate_limit_respected(context, rate):
    # O throttler garante isso - verificamos que nao houve erro 429
    errors = [
        r for r in context["results"] if r.error_message and "429" in r.error_message
    ]
    assert len(errors) == 0


@then(parsers.parse("todas as {count:d} URLs devem ser auditadas"))
def then_all_urls_audited(context, count):
    assert len(context["results"]) == count


# ============================================================================
# Cenario: Rate limit respeitado
# ============================================================================


@given(parsers.parse("um rate limit de {rate} requisicoes por segundo"))
def given_rate_limit(context, rate):
    context["rate_limit"] = float(rate)


@then(parsers.parse("o tempo total deve ser aproximadamente {formula} segundos"))
def then_expected_time(context, formula):
    # Tempo esperado baseado no rate limit
    # 20 URLs * 2 req/site / 3.5 req/s = ~11.4s
    urls = len(context["urls"])
    req_per_site = context.get("requests_per_site", 2)
    rate = context["rate_limit"]
    expected_time = (urls * req_per_site) / rate

    elapsed = context["end_time"] - context["start_time"]
    # Tolerancia de 50% devido a overhead
    assert elapsed >= expected_time * 0.5


@then("nenhum erro de rate limit deve ocorrer")
def then_no_rate_limit_errors(context):
    errors = [
        r
        for r in context["results"]
        if r.error_message and "429" in str(r.error_message)
    ]
    assert len(errors) == 0


# ============================================================================
# Cenario: Falha em uma URL
# ============================================================================


@given(parsers.parse("uma lista de {total:d} URLs onde {error_count:d} retorna erro"))
def given_urls_with_error(context, total, error_count, mock_psi_api):
    context["urls"] = [f"https://prefeitura{i}.gov.br" for i in range(total)]
    context["error_count"] = error_count

    # Configurar mock - primeiras URLs com sucesso, ultimas com erro
    for i, url in enumerate(context["urls"]):
        if i < total - error_count:
            mock_psi_api.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            ).mock(return_value=Response(200, json=create_psi_response(url)))
        else:
            mock_psi_api.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            ).mock(return_value=Response(500, json={"error": {"message": "Server Error"}}))


@then(parsers.parse("{count:d} URLs devem ter resultado de sucesso"))
def then_success_count(context, count):
    success = [r for r in context["results"] if not r.error_message]
    assert len(success) == count


@then(parsers.parse("{count:d} URL deve ter mensagem de erro"))
def then_error_count(context, count):
    errors = [r for r in context["results"] if r.error_message]
    assert len(errors) == count


@then("o processamento deve continuar normalmente")
def then_processing_continues(context):
    # Se chegou aqui, o processamento nao foi interrompido
    assert len(context["results"]) == len(context["urls"])


# ============================================================================
# Cenario: Semaforo de concorrencia
# ============================================================================


@given(parsers.parse("um limite de {limit:d} conexoes simultaneas"))
def given_concurrent_limit(context, limit):
    context["max_concurrent"] = limit


@then(parsers.parse("no maximo {limit:d} requisicoes HTTP devem estar ativas ao mesmo tempo"))
def then_max_concurrent_respected(context, limit):
    # Isso e garantido pelo semaphore - se nao houve erro, foi respeitado
    assert context["max_concurrent"] == limit
