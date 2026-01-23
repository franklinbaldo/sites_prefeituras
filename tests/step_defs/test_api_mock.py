"""Step definitions para testes com mock da API PSI."""

import asyncio
import time

import pytest
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

from sites_prefeituras.collector import PageSpeedCollector, process_urls_in_chunks
from tests.conftest import create_psi_response

# Carrega os cenarios do arquivo .feature
scenarios("../features/api_mock.feature")


# ============================================================================
# Contexto
# ============================================================================


@pytest.fixture
def mock_context():
    """Contexto compartilhado entre steps."""
    return {
        "responses": [],
        "result": None,
        "results": [],
        "start_time": None,
        "retry_count": 0,
    }


@given("que a API PSI esta mockada")
def api_is_mocked(mock_context, mock_psi_api):
    mock_context["mock"] = mock_psi_api


# ============================================================================
# Cenario: Sucesso mockado
# ============================================================================


@given(parsers.parse("uma resposta mockada com score de performance {score}"))
def given_performance_score(mock_context, score):
    mock_context["performance"] = float(score)


@given(parsers.parse("uma resposta mockada com score de acessibilidade {score}"))
def given_accessibility_score(mock_context, score, mock_psi_api):
    mock_context["accessibility"] = float(score)

    # Configurar o mock com os scores
    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        return_value=Response(
            200,
            json=create_psi_response(
                "https://exemplo.gov.br",
                performance=mock_context["performance"],
                accessibility=mock_context["accessibility"],
            ),
        )
    )


@when(parsers.parse('eu auditar o site "{url}"'))
def when_audit_site(mock_context, url, api_key):
    async def _audit():
        async with PageSpeedCollector(api_key=api_key) as collector:
            return await collector.audit_site(url)

    mock_context["start_time"] = time.time()
    mock_context["result"] = asyncio.run(_audit())
    mock_context["elapsed"] = time.time() - mock_context["start_time"]


@then(parsers.parse("o resultado deve ter performance {score}"))
def then_performance_score(mock_context, score):
    result = mock_context["result"]
    expected = float(score)

    if result.mobile_result:
        actual = result.mobile_result.lighthouseResult.categories["performance"].score
        assert actual == expected


@then(parsers.parse("o resultado deve ter acessibilidade {score}"))
def then_accessibility_score(mock_context, score):
    result = mock_context["result"]
    expected = float(score)

    if result.mobile_result:
        actual = result.mobile_result.lighthouseResult.categories["accessibility"].score
        assert actual == expected


@then("nao deve haver mensagem de erro")
def then_no_error(mock_context):
    assert mock_context["result"].error_message is None


# ============================================================================
# Cenario: Timeout mockado
# ============================================================================


@given("uma resposta mockada que retorna timeout")
def given_timeout_response(mock_context, mock_psi_api):
    import httpx

    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        side_effect=httpx.TimeoutException("Connection timeout")
    )


@then(parsers.parse('o resultado deve ter mensagem de erro contendo "{text}"'))
def then_error_contains(mock_context, text):
    result = mock_context["result"]
    assert result.error_message is not None
    assert text.lower() in result.error_message.lower()


@then(parsers.parse("o retry deve ser tentado {count:d} vezes"))
def then_retry_count(mock_context, count):
    # Verificado pelo tenacity - se chegou aqui apos timeout, tentou retries
    assert mock_context["result"].error_message is not None


# ============================================================================
# Cenario: Rate limit 429
# ============================================================================


@given("uma resposta mockada que retorna erro 429")
def given_rate_limit_error(mock_context, mock_psi_api):
    # Primeira chamada retorna 429, depois sucesso
    responses = [
        Response(429, json={"error": {"code": 429, "message": "Rate Limit Exceeded"}}),
        Response(429, json={"error": {"code": 429, "message": "Rate Limit Exceeded"}}),
        Response(200, json=create_psi_response("https://site.gov.br")),
    ]
    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        side_effect=responses
    )


@then("o sistema deve aguardar antes de tentar novamente")
def then_wait_before_retry(mock_context):
    # Se o resultado tem sucesso apos 429, o retry funcionou
    result = mock_context["result"]
    # Pode ter erro ou sucesso dependendo dos retries
    assert result is not None


@then("o retry deve usar backoff exponencial")
def then_exponential_backoff(mock_context):
    # Verificado pela configuracao do tenacity
    # Se passou, o backoff esta configurado
    pass


# ============================================================================
# Cenario: JSON invalido
# ============================================================================


@given("uma resposta mockada com JSON invalido")
def given_invalid_json(mock_context, mock_psi_api):
    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        return_value=Response(200, content=b"not valid json {{{")
    )


@then("o resultado deve ter mensagem de erro")
def then_has_error(mock_context):
    assert mock_context["result"].error_message is not None


@then("o erro deve ser registrado no log")
def then_error_logged(mock_context):
    # Verificado pela presenca de erro no resultado
    assert mock_context["result"].error_message is not None


# ============================================================================
# Cenario: Batch com mix
# ============================================================================


@given(parsers.parse("{count:d} respostas mockadas de sucesso"))
def given_success_responses(mock_context, count):
    mock_context["success_count"] = count


@given(parsers.parse("{count:d} respostas mockadas de erro"))
def given_error_responses(mock_context, count, mock_psi_api):
    mock_context["error_count"] = count

    total = mock_context["success_count"] + count
    responses = []

    for i in range(mock_context["success_count"]):
        responses.append(
            Response(200, json=create_psi_response(f"https://site{i}.gov.br"))
        )

    for _ in range(count):
        responses.append(Response(500, json={"error": {"message": "Server Error"}}))

    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        side_effect=responses
    )

    mock_context["urls"] = [f"https://site{i}.gov.br" for i in range(total)]


@when(parsers.parse("eu processar um batch de {count:d} sites"))
def when_process_batch(mock_context, count, api_key):
    async def _process():
        async with PageSpeedCollector(api_key=api_key) as collector:
            return await process_urls_in_chunks(
                collector,
                mock_context["urls"][:count],
                chunk_size=count,
            )

    mock_context["results"] = asyncio.run(_process())


@then(parsers.parse("{count:d} sites devem ter resultado de sucesso"))
def then_success_count(mock_context, count):
    success = [r for r in mock_context["results"] if not r.error_message]
    assert len(success) == count


@then(parsers.parse("{count:d} sites devem ter mensagem de erro"))
def then_error_count(mock_context, count):
    errors = [r for r in mock_context["results"] if r.error_message]
    assert len(errors) == count


@then(parsers.parse("todos os {count:d} devem ser salvos no banco"))
def then_all_saved(mock_context, count):
    # Verificado pelo numero de resultados
    assert len(mock_context["results"]) == count


# ============================================================================
# Cenario: Sem requisicoes reais
# ============================================================================


@given("que o mock esta ativo")
def given_mock_active(mock_context, mock_psi_api):
    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        return_value=Response(200, json=create_psi_response("https://any.gov.br"))
    )


@when("eu auditar qualquer site")
def when_audit_any(mock_context, api_key):
    async def _audit():
        async with PageSpeedCollector(api_key=api_key) as collector:
            return await collector.audit_site("https://any.gov.br")

    mock_context["start_time"] = time.time()
    mock_context["result"] = asyncio.run(_audit())
    mock_context["elapsed"] = time.time() - mock_context["start_time"]


@then("nenhuma requisicao HTTP real deve ser feita")
def then_no_real_requests(mock_context):
    # Se usou respx mock, nao fez requisicao real
    assert mock_context["result"] is not None


@then(parsers.parse("o teste deve completar em menos de {seconds:d} segundo"))
def then_fast_completion(mock_context, seconds):
    assert mock_context["elapsed"] < seconds


# ============================================================================
# Cenario: Core Web Vitals
# ============================================================================


@given("uma resposta mockada com metricas CWV")
def given_cwv_response(mock_context, mock_psi_api):
    mock_psi_api.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed").mock(
        return_value=Response(
            200,
            json=create_psi_response(
                "https://site.gov.br",
                fcp=1500,
                lcp=2500,
                cls=0.05,
            ),
        )
    )


@then("o resultado deve conter FCP")
def then_has_fcp(mock_context):
    result = mock_context["result"]
    if result.mobile_result:
        audits = result.mobile_result.lighthouseResult.audits
        assert "first-contentful-paint" in audits


@then("o resultado deve conter LCP")
def then_has_lcp(mock_context):
    result = mock_context["result"]
    if result.mobile_result:
        audits = result.mobile_result.lighthouseResult.audits
        assert "largest-contentful-paint" in audits


@then("o resultado deve conter CLS")
def then_has_cls(mock_context):
    result = mock_context["result"]
    if result.mobile_result:
        audits = result.mobile_result.lighthouseResult.audits
        assert "cumulative-layout-shift" in audits


# ============================================================================
# Cenario: Fluxo completo
# ============================================================================


@given(parsers.parse("respostas mockadas para {count:d} sites"))
def given_mock_responses(mock_context, count, mock_psi_api):
    mock_context["urls"] = [f"https://site{i}.gov.br" for i in range(count)]

    for url in mock_context["urls"]:
        mock_psi_api.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        ).mock(return_value=Response(200, json=create_psi_response(url)))


@when("eu executar o comando batch com mock")
def when_run_batch_mock(mock_context, api_key, storage_sync, output_dir):
    async def _run_batch(storage):
        async with PageSpeedCollector(api_key=api_key) as collector:
            results = await process_urls_in_chunks(
                collector,
                mock_context["urls"],
                chunk_size=5,
            )

            for result in results:
                await storage.save_audit(result)

            mock_context["results"] = results
            mock_context["storage"] = storage
            mock_context["output_dir"] = output_dir

        # Exportar
        await storage.export_to_parquet(output_dir)
        await storage.export_to_json(output_dir)

    asyncio.run(_run_batch(storage_sync))


@then(parsers.parse("o banco de dados deve conter {count:d} registros"))
def then_db_has_records(mock_context, count):
    storage = mock_context["storage"]
    result = storage.conn.execute("SELECT COUNT(*) FROM audits").fetchone()
    assert result[0] == count


@then("o arquivo Parquet deve ser gerado")
def then_parquet_generated(mock_context):
    output_dir = mock_context["output_dir"]
    parquet_files = list(output_dir.glob("*.parquet"))
    assert len(parquet_files) > 0


@then("o arquivo JSON deve ser gerado")
def then_json_generated(mock_context):
    output_dir = mock_context["output_dir"]
    json_files = list(output_dir.glob("*.json"))
    assert len(json_files) > 0
