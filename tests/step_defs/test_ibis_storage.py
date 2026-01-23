"""Step definitions para camada de armazenamento Ibis."""

import asyncio
import json
from datetime import datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sites_prefeituras.models import PageSpeedInsightsResult, SiteAudit
from tests.conftest import create_psi_response

# Carrega os cenarios do arquivo .feature
scenarios("../features/ibis_storage.feature")


# ============================================================================
# Contexto
# ============================================================================


@pytest.fixture
def ibis_context():
    """Contexto compartilhado entre steps."""
    return {
        "storage": None,
        "result": None,
        "metrics": None,
        "sites": [],
        "ranking": [],
        "output_dir": None,
    }


@given("uma conexao Ibis com DuckDB em memoria")
def given_ibis_connection(ibis_context, storage_sync):
    """Initialize Ibis connection with DuckDB."""
    ibis_context["storage"] = storage_sync


# ============================================================================
# Esquemas e Tabelas
# ============================================================================


@when("eu criar as tabelas via Ibis")
def when_create_tables(ibis_context):
    # Tables are already created during storage initialization
    pass


@then(parsers.parse('a tabela "{table_name}" deve existir'))
def then_table_exists(ibis_context, table_name):
    storage = ibis_context["storage"]
    tables = storage.con.list_tables()
    assert table_name in tables


@given("que as tabelas foram criadas via Ibis")
def given_tables_created(ibis_context, storage_sync):
    ibis_context["storage"] = storage_sync


@when(parsers.parse('eu consultar o esquema da tabela "{table_name}"'))
def when_query_schema(ibis_context, table_name):
    storage = ibis_context["storage"]
    table = storage.con.table(table_name)
    ibis_context["schema"] = table.schema()


@then(parsers.parse('deve ter a coluna "{column}" do tipo inteiro'))
def then_has_integer_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    assert "int" in str(schema[column]).lower()


@then(parsers.parse('deve ter a coluna "{column}" do tipo string'))
def then_has_string_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    col_type = str(schema[column]).lower()
    assert "string" in col_type or "varchar" in col_type


@then(parsers.parse('deve ter a coluna "{column}" do tipo timestamp'))
def then_has_timestamp_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    assert "timestamp" in str(schema[column]).lower()


@then(parsers.parse('deve ter a coluna "{column}" do tipo JSON'))
def then_has_json_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    col_type = str(schema[column]).lower()
    # JSON can be stored as json or string in different backends
    assert "json" in col_type or "string" in col_type or "varchar" in col_type


@then(parsers.parse('deve ter a coluna "{column}" do tipo float'))
def then_has_float_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    col_type = str(schema[column]).lower()
    assert "float" in col_type or "double" in col_type


@then(parsers.parse('deve ter a coluna "{column}" do tipo boolean'))
def then_has_boolean_column(ibis_context, column):
    schema = ibis_context["schema"]
    assert column in schema.names
    col_type = str(schema[column]).lower()
    assert "bool" in col_type


# ============================================================================
# Operacoes CRUD
# ============================================================================


@when(parsers.parse('eu inserir uma auditoria para "{url}"'))
def when_insert_audit(ibis_context, url):
    storage = ibis_context["storage"]

    # Create mock PSI response
    psi_data = create_psi_response(url)
    mobile_result = PageSpeedInsightsResult(**psi_data)
    desktop_result = PageSpeedInsightsResult(**psi_data)

    audit = SiteAudit(
        url=url,
        timestamp=datetime.utcnow(),
        mobile_result=mobile_result,
        desktop_result=desktop_result,
    )

    audit_id = asyncio.run(storage.save_audit(audit))
    ibis_context["audit_id"] = audit_id


@then("a auditoria deve ser salva com sucesso")
def then_audit_saved(ibis_context):
    assert ibis_context.get("audit_id") is not None
    assert ibis_context["audit_id"] > 0


@then("o resumo deve ser criado automaticamente")
def then_summary_created(ibis_context):
    storage = ibis_context["storage"]
    count = storage.summaries.count().execute()
    assert count > 0


@given("auditorias salvas nas ultimas 24 horas")
def given_recent_audits(ibis_context, storage_sync):
    ibis_context["storage"] = storage_sync

    # Insert recent audits
    for i, url in enumerate(["https://site1.sp.gov.br", "https://site2.rj.gov.br"]):
        psi_data = create_psi_response(url)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow() - timedelta(hours=i),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when("eu consultar URLs auditadas recentemente")
def when_query_recent_urls(ibis_context):
    storage = ibis_context["storage"]
    urls = asyncio.run(storage.get_recently_audited_urls(hours=24))
    ibis_context["recent_urls"] = urls


@then("devo receber a lista de URLs distintas")
def then_receive_urls(ibis_context):
    urls = ibis_context["recent_urls"]
    assert len(urls) > 0


@when(parsers.parse('eu adicionar "{url}" a quarentena com {failures:d} falhas'))
def when_add_to_quarantine(ibis_context, url, failures):
    storage = ibis_context["storage"]
    now = datetime.utcnow()

    storage.conn.execute(
        """
        INSERT INTO quarantine (id, url, first_failure, last_failure, consecutive_failures, status, version, valid_from)
        VALUES (?, ?, ?, ?, ?, 'quarantined', ?, ?)
    """,
        [1, url, now - timedelta(days=failures), now, failures, 1, now],
    )
    ibis_context["test_url"] = url


@then("o site deve aparecer na lista de quarentena")
def then_site_in_quarantine(ibis_context):
    storage = ibis_context["storage"]
    url = ibis_context["test_url"]
    sites = asyncio.run(storage.get_quarantined_sites())
    urls = [s["url"] for s in sites]
    assert url in urls


@then(parsers.parse('deve ter status "{status}"'))
def then_has_status(ibis_context, status):
    storage = ibis_context["storage"]
    url = ibis_context["test_url"]
    sites = asyncio.run(storage.get_quarantined_sites())
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert site["status"] == status


# ============================================================================
# Consultas Agregadas
# ============================================================================


@given(parsers.parse("{count:d} auditorias com scores variados"))
def given_varied_audits(ibis_context, count, storage_sync):
    ibis_context["storage"] = storage_sync

    for i in range(count):
        url = f"https://site{i}.sp.gov.br"
        perf = 0.3 + (i / count) * 0.6  # 0.3 to 0.9
        psi_data = create_psi_response(url, performance=perf)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when("eu calcular as metricas agregadas via Ibis")
def when_calculate_metrics(ibis_context):
    storage = ibis_context["storage"]
    metrics = asyncio.run(storage.get_aggregated_metrics())
    ibis_context["metrics"] = metrics


@then("devo receber o total de auditorias")
def then_receive_total(ibis_context):
    assert "total_audits" in ibis_context["metrics"]
    assert ibis_context["metrics"]["total_audits"] > 0


@then("devo receber a media de performance mobile")
def then_receive_avg_performance(ibis_context):
    assert "avg_mobile_performance" in ibis_context["metrics"]


@then("devo receber o desvio padrao")
def then_receive_std(ibis_context):
    assert "std_mobile_performance" in ibis_context["metrics"]


@given("auditorias de sites de SP, RJ e MG")
def given_state_audits(ibis_context, storage_sync):
    ibis_context["storage"] = storage_sync

    urls = [
        "https://campinas.sp.gov.br",
        "https://niteroi.rj.gov.br",
        "https://uberlandia.mg.gov.br",
    ]

    for url in urls:
        psi_data = create_psi_response(url)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when("eu agrupar metricas por estado via Ibis")
def when_group_by_state(ibis_context):
    storage = ibis_context["storage"]
    states = asyncio.run(storage.get_metrics_by_state())
    ibis_context["states"] = states


@then(parsers.parse("devo ver {state} na lista de estados"))
def then_state_in_list(ibis_context, state):
    states = [s["state"] for s in ibis_context["states"]]
    assert state in states


@given(parsers.parse("{count:d} auditorias com performance variada"))
def given_varied_performance(ibis_context, count, storage_sync):
    ibis_context["storage"] = storage_sync

    for i in range(count):
        url = f"https://perf{i}.sp.gov.br"
        perf = 0.1 + (i / count) * 0.8
        psi_data = create_psi_response(url, performance=perf)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when(parsers.parse("eu consultar os {limit:d} piores sites via Ibis"))
def when_query_worst(ibis_context, limit):
    storage = ibis_context["storage"]
    sites = asyncio.run(storage.get_worst_performing_sites(limit=limit))
    ibis_context["sites"] = sites


@then(parsers.parse("devo receber {count:d} sites"))
def then_receive_count(ibis_context, count):
    assert len(ibis_context["sites"]) == count


@then("o primeiro deve ter a menor performance")
def then_first_worst(ibis_context):
    sites = ibis_context["sites"]
    if len(sites) > 1:
        assert sites[0]["mobile_performance"] <= sites[1]["mobile_performance"]


@given(parsers.parse("{count:d} auditorias com acessibilidade variada"))
def given_varied_accessibility(ibis_context, count, storage_sync):
    ibis_context["storage"] = storage_sync

    for i in range(count):
        url = f"https://access{i}.sp.gov.br"
        acc = 0.1 + (i / count) * 0.8
        psi_data = create_psi_response(url, accessibility=acc)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when(
    parsers.parse("eu consultar os {limit:d} melhores sites em acessibilidade via Ibis")
)
def when_query_best_accessibility(ibis_context, limit):
    storage = ibis_context["storage"]
    sites = asyncio.run(storage.get_best_accessibility_sites(limit=limit))
    ibis_context["sites"] = sites


@then("o primeiro deve ter a maior acessibilidade")
def then_first_best(ibis_context):
    sites = ibis_context["sites"]
    if len(sites) > 1:
        assert sites[0]["mobile_accessibility"] >= sites[1]["mobile_accessibility"]


# ============================================================================
# Quarentena
# ============================================================================


@given(
    parsers.parse('auditorias com falhas em {days:d} dias consecutivos para "{url}"')
)
def given_consecutive_failures(ibis_context, days, url, storage_sync):
    ibis_context["storage"] = storage_sync
    ibis_context["test_url"] = url

    for i in range(days):
        storage_sync.conn.execute(
            """
            INSERT INTO audits (id, url, timestamp, error_message)
            VALUES (?, ?, ?, ?)
        """,
            [i + 1, url, datetime.utcnow() - timedelta(days=i), "Connection timeout"],
        )


@when(parsers.parse("eu atualizar a quarentena via Ibis com minimo de {days:d} dias"))
def when_update_quarantine(ibis_context, days):
    storage = ibis_context["storage"]
    result = asyncio.run(storage.update_quarantine(min_consecutive_days=days))
    ibis_context["update_result"] = result


@then(parsers.parse('"{url}" deve entrar na quarentena'))
def then_url_in_quarantine(ibis_context, url):
    storage = ibis_context["storage"]
    sites = asyncio.run(storage.get_quarantined_sites())
    urls = [s["url"] for s in sites]
    assert url in urls


@then(parsers.parse("deve ter {count:d} falhas consecutivas registradas"))
def then_failure_count(ibis_context, count):
    storage = ibis_context["storage"]
    url = ibis_context["test_url"]
    sites = asyncio.run(storage.get_quarantined_sites())
    site = next((s for s in sites if s["url"] == url), None)
    assert site is not None
    assert site["consecutive_failures"] >= count


@given(parsers.parse('{count:d} sites em quarentena com status "{status}"'))
def given_quarantine_sites(ibis_context, count, status, storage_sync):
    ibis_context["storage"] = storage_sync

    if "id_counter" not in ibis_context:
        ibis_context["id_counter"] = 0

    for i in range(count):
        ibis_context["id_counter"] += 1
        url = f"https://q-{status}-{i}.gov.br"
        now = datetime.utcnow()
        storage_sync.conn.execute(
            """
            INSERT INTO quarantine (id, url, first_failure, last_failure, consecutive_failures, status, version, valid_from)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                ibis_context["id_counter"],
                url,
                now - timedelta(days=5),
                now,
                5,
                status,
                1,
                now,
            ],
        )


@when("eu consultar estatisticas da quarentena via Ibis")
def when_query_quarantine_stats(ibis_context):
    storage = ibis_context["storage"]
    stats = asyncio.run(storage.get_quarantine_stats())
    ibis_context["stats"] = stats


@then(parsers.parse("o total deve ser {count:d}"))
def then_total_count(ibis_context, count):
    assert ibis_context["stats"]["total"] == count


@then(parsers.parse("o total em quarentena deve ser {count:d}"))
def then_quarantined_count(ibis_context, count):
    assert ibis_context["stats"]["quarantined"] == count


@then(parsers.parse("o total em investigacao deve ser {count:d}"))
def then_investigating_count(ibis_context, count):
    assert ibis_context["stats"]["investigating"] == count


@given("sites em quarentena com varios status")
def given_various_quarantine_status(ibis_context, storage_sync):
    ibis_context["storage"] = storage_sync

    statuses = ["quarantined", "wrong_url", "investigating"]
    for i, status in enumerate(statuses):
        now = datetime.utcnow()
        storage_sync.conn.execute(
            """
            INSERT INTO quarantine (id, url, first_failure, last_failure, consecutive_failures, status, version, valid_from)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                i + 1,
                f"https://mixed-{i}.gov.br",
                now - timedelta(days=5),
                now,
                5,
                status,
                1,
                now,
            ],
        )


@when("eu obter URLs para pular via Ibis")
def when_get_skip_urls(ibis_context):
    storage = ibis_context["storage"]
    urls = asyncio.run(storage.get_urls_to_skip_quarantine())
    ibis_context["skip_urls"] = urls


@then(parsers.parse('URLs com status "{status}" devem ser retornadas'))
def then_status_urls_returned(ibis_context, status):
    storage = ibis_context["storage"]
    sites = asyncio.run(storage.get_quarantined_sites(status=status))
    skip_urls = ibis_context["skip_urls"]

    for site in sites:
        assert site["url"] in skip_urls


@then(parsers.parse('URLs com status "{status}" nao devem ser retornadas'))
def then_status_urls_not_returned(ibis_context, status):
    storage = ibis_context["storage"]
    sites = asyncio.run(storage.get_quarantined_sites(status=status))
    skip_urls = ibis_context["skip_urls"]

    for site in sites:
        assert site["url"] not in skip_urls


# ============================================================================
# Evolucao Temporal
# ============================================================================


@given(parsers.parse("{count:d} auditorias do mesmo site em datas diferentes"))
def given_temporal_audits(ibis_context, count, storage_sync):
    ibis_context["storage"] = storage_sync
    url = "https://temporal.sp.gov.br"
    ibis_context["temporal_url"] = url

    for i in range(count):
        perf = 0.5 + (i / count) * 0.3
        psi_data = create_psi_response(url, performance=perf)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow() - timedelta(days=count - i),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when("eu consultar a evolucao temporal via Ibis")
def when_query_temporal(ibis_context):
    storage = ibis_context["storage"]
    url = ibis_context["temporal_url"]
    data = asyncio.run(storage.get_temporal_evolution(url))
    ibis_context["temporal_data"] = data


@then(parsers.parse("devo receber {count:d} registros ordenados por data"))
def then_temporal_records(ibis_context, count):
    data = ibis_context["temporal_data"]
    assert len(data) == count


@then("cada registro deve ter metricas de performance")
def then_temporal_has_metrics(ibis_context):
    data = ibis_context["temporal_data"]
    for record in data:
        assert "mobile_performance" in record


# ============================================================================
# Ranking e Dashboard
# ============================================================================


@given(parsers.parse("{count:d} auditorias de sites diferentes"))
def given_different_sites(ibis_context, count, storage_sync):
    ibis_context["storage"] = storage_sync

    for i in range(count):
        url = f"https://ranking{i}.sp.gov.br"
        acc = 0.3 + (i / count) * 0.6
        psi_data = create_psi_response(url, accessibility=acc)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))


@when("eu gerar o ranking via Ibis")
def when_generate_ranking(ibis_context, tmp_path):
    storage = ibis_context["storage"]
    output_dir = tmp_path / "dashboard"
    output_dir.mkdir()
    ibis_context["output_dir"] = output_dir

    result = asyncio.run(storage.export_dashboard_json(output_dir))
    ibis_context["dashboard_result"] = result

    # Load ranking
    ranking_file = output_dir / "ranking.json"
    with open(ranking_file) as f:
        data = json.load(f)
        ibis_context["ranking"] = data["sites"]


@then("cada site deve aparecer apenas uma vez")
def then_unique_sites(ibis_context):
    ranking = ibis_context["ranking"]
    urls = [s["url"] for s in ranking]
    assert len(urls) == len(set(urls))


@then("devem estar ordenados por acessibilidade")
def then_ordered_by_accessibility(ibis_context):
    ranking = ibis_context["ranking"]
    if len(ranking) > 1:
        for i in range(len(ranking) - 1):
            assert ranking[i]["score"] >= ranking[i + 1]["score"]


@then("cada registro deve ter posicao no ranking")
def then_has_rank(ibis_context):
    ranking = ibis_context["ranking"]
    for site in ranking:
        assert "rank" in site


@given("auditorias e quarentena populadas")
def given_populated_data(ibis_context, storage_sync):
    ibis_context["storage"] = storage_sync

    # Add audits
    for i in range(5):
        url = f"https://dashboard{i}.sp.gov.br"
        psi_data = create_psi_response(url)
        mobile_result = PageSpeedInsightsResult(**psi_data)

        audit = SiteAudit(
            url=url,
            timestamp=datetime.utcnow(),
            mobile_result=mobile_result,
            desktop_result=mobile_result,
        )
        asyncio.run(storage_sync.save_audit(audit))

    # Add quarantine
    now = datetime.utcnow()
    storage_sync.conn.execute(
        """
        INSERT INTO quarantine (id, url, first_failure, last_failure, consecutive_failures, status, version, valid_from)
        VALUES (?, ?, ?, ?, ?, 'quarantined', ?, ?)
    """,
        [1, "https://problema.gov.br", now - timedelta(days=5), now, 5, 1, now],
    )


@when("eu exportar dados para dashboard via Ibis")
def when_export_dashboard(ibis_context, tmp_path):
    storage = ibis_context["storage"]
    output_dir = tmp_path / "dashboard_export"
    output_dir.mkdir()
    ibis_context["output_dir"] = output_dir

    result = asyncio.run(storage.export_dashboard_json(output_dir))
    ibis_context["dashboard_result"] = result


@then(parsers.parse('o arquivo "{filename}" deve ser criado'))
def then_file_created(ibis_context, filename):
    output_dir = ibis_context["output_dir"]
    assert (output_dir / filename).exists()
