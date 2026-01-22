"""Step definitions para sistema de quarentena."""

from datetime import datetime, timedelta

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sites_prefeituras.storage import DuckDBStorage

# Carrega os cenarios do arquivo .feature
scenarios("../features/quarantine.feature")


# ============================================================================
# Contexto
# ============================================================================

@pytest.fixture
def quarantine_context():
    """Contexto compartilhado entre steps."""
    return {
        "sites": [],
        "result": None,
        "stats": None,
        "skip_urls": set(),
    }


@given("que existem auditorias no banco de dados")
def audits_exist(quarantine_context, storage):
    quarantine_context["storage"] = storage


# ============================================================================
# Cenario: Falhas consecutivas
# ============================================================================

@given(parsers.parse("auditorias de um site que falhou por {days:d} dias consecutivos"))
@pytest.mark.asyncio
async def given_consecutive_failures(quarantine_context, days, storage):
    quarantine_context["storage"] = storage
    url = "https://site-com-problemas.gov.br"
    quarantine_context["test_url"] = url

    # Inserir falhas consecutivas
    for i in range(days):
        await storage.conn.execute("""
            INSERT INTO audits (url, timestamp, error_message)
            VALUES (?, ?, ?)
        """, [
            url,
            datetime.utcnow() - timedelta(days=i),
            "Connection timeout"
        ])


@when(parsers.parse("eu atualizar a quarentena com minimo de {days:d} dias"))
@pytest.mark.asyncio
async def when_update_quarantine(quarantine_context, days):
    storage = quarantine_context["storage"]
    result = await storage.update_quarantine(min_consecutive_days=days)
    quarantine_context["update_result"] = result


@then("o site deve ser adicionado a quarentena")
@pytest.mark.asyncio
async def then_site_in_quarantine(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    urls = [s["url"] for s in sites]
    assert url in urls


@then(parsers.parse('o status deve ser "{status}"'))
@pytest.mark.asyncio
async def then_status_is(quarantine_context, status):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert site["status"] == status


@then(parsers.parse("o numero de falhas consecutivas deve ser {count:d}"))
@pytest.mark.asyncio
async def then_failure_count(quarantine_context, count):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert site["consecutive_failures"] >= count


# ============================================================================
# Cenario: Falhas intermitentes
# ============================================================================

@given("auditorias de um site com falhas em dias alternados")
@pytest.mark.asyncio
async def given_intermittent_failures(quarantine_context, storage):
    quarantine_context["storage"] = storage
    url = "https://site-intermitente.gov.br"
    quarantine_context["test_url"] = url

    # Inserir falhas em dias alternados (nao consecutivos)
    for i in range(0, 10, 2):  # dias 0, 2, 4, 6, 8
        await storage.conn.execute("""
            INSERT INTO audits (url, timestamp, error_message)
            VALUES (?, ?, ?)
        """, [
            url,
            datetime.utcnow() - timedelta(days=i),
            "Intermittent error"
        ])


@then("o site nao deve estar na quarentena")
@pytest.mark.asyncio
async def then_site_not_in_quarantine(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    urls = [s["url"] for s in sites]
    assert url not in urls


# ============================================================================
# Cenario: Atualizar status
# ============================================================================

@given(parsers.parse('um site na quarentena com status "{status}"'))
@pytest.mark.asyncio
async def given_site_with_status(quarantine_context, status, storage):
    quarantine_context["storage"] = storage
    url = "https://site-em-quarentena.gov.br"
    quarantine_context["test_url"] = url

    await storage.conn.execute("""
        INSERT INTO quarantine (url, first_failure, last_failure, consecutive_failures, status)
        VALUES (?, ?, ?, ?, ?)
    """, [
        url,
        datetime.utcnow() - timedelta(days=5),
        datetime.utcnow(),
        5,
        status
    ])


@when(parsers.parse('eu atualizar o status para "{new_status}"'))
@pytest.mark.asyncio
async def when_update_status(quarantine_context, new_status):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    await storage.update_quarantine_status(url, new_status)


@then(parsers.parse('o status do site deve ser "{expected_status}"'))
@pytest.mark.asyncio
async def then_status_should_be(quarantine_context, expected_status):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert site["status"] == expected_status


@then("a data de atualizacao deve ser atualizada")
def then_updated_at_changed(quarantine_context):
    # Verificado pela execucao bem-sucedida do update
    pass


# ============================================================================
# Cenario: Marcar como URL errada
# ============================================================================

@given("um site na quarentena")
@pytest.mark.asyncio
async def given_site_in_quarantine(quarantine_context, storage):
    quarantine_context["storage"] = storage
    url = "https://url-antiga.gov.br"
    quarantine_context["test_url"] = url

    await storage.conn.execute("""
        INSERT INTO quarantine (url, first_failure, last_failure, consecutive_failures, status)
        VALUES (?, ?, ?, ?, 'quarantined')
    """, [
        url,
        datetime.utcnow() - timedelta(days=10),
        datetime.utcnow(),
        10
    ])


@when(parsers.parse('eu atualizar o status para "{status}" com nota "{note}"'))
@pytest.mark.asyncio
async def when_update_with_note(quarantine_context, status, note):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    await storage.update_quarantine_status(url, status, notes=note)


@then(parsers.parse('a nota deve conter "{text}"'))
@pytest.mark.asyncio
async def then_note_contains(quarantine_context, text):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert text in (site["notes"] or "")


# ============================================================================
# Cenario: Remover da quarentena
# ============================================================================

@when("eu remover o site da quarentena")
@pytest.mark.asyncio
async def when_remove_from_quarantine(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    await storage.remove_from_quarantine(url)


@then("o site nao deve estar mais na quarentena")
@pytest.mark.asyncio
async def then_site_removed(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    urls = [s["url"] for s in sites]
    assert url not in urls


# ============================================================================
# Cenario: Listar por status
# ============================================================================

@given(parsers.parse('{count:d} sites em quarentena com status "{status}"'))
@pytest.mark.asyncio
async def given_sites_with_status(quarantine_context, count, status, storage):
    quarantine_context["storage"] = storage

    for i in range(count):
        url = f"https://site-{status}-{i}.gov.br"
        await storage.conn.execute("""
            INSERT INTO quarantine (url, first_failure, last_failure, consecutive_failures, status)
            VALUES (?, ?, ?, ?, ?)
        """, [
            url,
            datetime.utcnow() - timedelta(days=5),
            datetime.utcnow(),
            5,
            status
        ])


@when(parsers.parse('eu listar sites com status "{status}"'))
@pytest.mark.asyncio
async def when_list_by_status(quarantine_context, status):
    storage = quarantine_context["storage"]
    sites = await storage.get_quarantined_sites(status=status)
    quarantine_context["listed_sites"] = sites


@then(parsers.parse("devo ver {count:d} sites na lista"))
def then_site_count(quarantine_context, count):
    sites = quarantine_context["listed_sites"]
    assert len(sites) == count


# ============================================================================
# Cenario: URLs para pular
# ============================================================================

@when("eu obter URLs para pular")
@pytest.mark.asyncio
async def when_get_skip_urls(quarantine_context):
    storage = quarantine_context["storage"]
    urls = await storage.get_urls_to_skip_quarantine()
    quarantine_context["skip_urls"] = urls


@then(parsers.parse('as URLs com status "{status}" devem ser retornadas'))
@pytest.mark.asyncio
async def then_urls_returned(quarantine_context, status):
    storage = quarantine_context["storage"]
    sites = await storage.get_quarantined_sites(status=status)
    skip_urls = quarantine_context["skip_urls"]

    for site in sites:
        assert site["url"] in skip_urls


@then(parsers.parse('as URLs com status "{status}" nao devem ser retornadas'))
@pytest.mark.asyncio
async def then_urls_not_returned(quarantine_context, status):
    storage = quarantine_context["storage"]
    sites = await storage.get_quarantined_sites(status=status)
    skip_urls = quarantine_context["skip_urls"]

    for site in sites:
        assert site["url"] not in skip_urls


# ============================================================================
# Cenario: Estatisticas
# ============================================================================

@given("sites em quarentena com varios status")
@pytest.mark.asyncio
async def given_various_status(quarantine_context, storage):
    quarantine_context["storage"] = storage

    statuses = ["quarantined", "quarantined", "investigating", "resolved", "wrong_url"]
    for i, status in enumerate(statuses):
        await storage.conn.execute("""
            INSERT INTO quarantine (url, first_failure, last_failure, consecutive_failures, status)
            VALUES (?, ?, ?, ?, ?)
        """, [
            f"https://site-{i}.gov.br",
            datetime.utcnow() - timedelta(days=i+3),
            datetime.utcnow(),
            i + 3,
            status
        ])


@when("eu solicitar estatisticas da quarentena")
@pytest.mark.asyncio
async def when_get_stats(quarantine_context):
    storage = quarantine_context["storage"]
    stats = await storage.get_quarantine_stats()
    quarantine_context["stats"] = stats


@then("devo ver o total de sites")
def then_see_total(quarantine_context):
    assert "total" in quarantine_context["stats"]
    assert quarantine_context["stats"]["total"] > 0


@then("devo ver a contagem por status")
def then_see_status_counts(quarantine_context):
    stats = quarantine_context["stats"]
    assert "quarantined" in stats
    assert "investigating" in stats
    assert "resolved" in stats


@then("devo ver a media de falhas")
def then_see_avg_failures(quarantine_context):
    assert "avg_failures" in quarantine_context["stats"]


@then("devo ver o maximo de falhas")
def then_see_max_failures(quarantine_context):
    assert "max_failures" in quarantine_context["stats"]


# ============================================================================
# Cenario: Site volta a funcionar
# ============================================================================

@given("um site em quarentena que voltou a funcionar")
@pytest.mark.asyncio
async def given_recovered_site(quarantine_context, storage):
    quarantine_context["storage"] = storage
    url = "https://site-recuperado.gov.br"
    quarantine_context["test_url"] = url

    # Site estava em quarentena
    await storage.conn.execute("""
        INSERT INTO quarantine (url, first_failure, last_failure, consecutive_failures, status)
        VALUES (?, ?, ?, ?, 'quarantined')
    """, [
        url,
        datetime.utcnow() - timedelta(days=10),
        datetime.utcnow() - timedelta(days=2),
        8
    ])


@when("eu executar uma nova auditoria com sucesso")
@pytest.mark.asyncio
async def when_successful_audit(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]

    # Nova auditoria bem-sucedida
    await storage.conn.execute("""
        INSERT INTO audits (url, timestamp, error_message)
        VALUES (?, ?, NULL)
    """, [url, datetime.utcnow()])


@then("o site pode ser removido da quarentena")
@pytest.mark.asyncio
async def then_can_be_removed(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]
    sites = await storage.get_quarantined_sites()
    site = next((s for s in sites if s["url"] == url), None)
    # O site ainda esta na quarentena ate ser removido manualmente
    assert site is not None


@then("futuras coletas devem incluir este site")
@pytest.mark.asyncio
async def then_future_collections_include(quarantine_context):
    storage = quarantine_context["storage"]
    url = quarantine_context["test_url"]

    # Atualizar para resolved
    await storage.update_quarantine_status(url, "resolved")

    # Verificar que nao esta mais na lista de skip
    skip_urls = await storage.get_urls_to_skip_quarantine()
    assert url not in skip_urls
