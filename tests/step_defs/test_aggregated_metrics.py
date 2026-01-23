"""Step definitions para metricas agregadas."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sites_prefeituras.models import AuditSummary, SiteAudit
from sites_prefeituras.storage import DuckDBStorage

# Carrega os cenarios do arquivo .feature
scenarios("../features/aggregated_metrics.feature")


# ============================================================================
# Contexto
# ============================================================================


@pytest.fixture
def metrics_context():
    """Contexto compartilhado entre steps."""
    return {
        "audits": [],
        "metrics": None,
        "result": None,
        "output_file": None,
    }


@given("que existem auditorias no banco de dados")
def audits_exist(metrics_context, storage_sync):
    metrics_context["storage"] = storage_sync


# ============================================================================
# Cenario: Estatisticas gerais
# ============================================================================


@given(parsers.parse("{count:d} auditorias no banco de dados"))
def given_n_audits(metrics_context, count, storage_sync):
    metrics_context["storage"] = storage_sync

    # Inserir auditorias de teste
    for i in range(count):
        has_error = i % 10 == 0  # 10% com erro
        storage_sync.conn.execute(
            """
            INSERT INTO audits (id, url, timestamp, error_message)
            VALUES (?, ?, ?, ?)
        """,
            [
                i + 1,
                f"https://prefeitura{i}.gov.br",
                datetime.utcnow() - timedelta(hours=i),
                "Timeout error" if has_error else None,
            ],
        )

        # Inserir summary
        storage_sync.conn.execute(
            """
            INSERT INTO audit_summaries (id, url, timestamp, mobile_performance, desktop_performance,
                mobile_accessibility, desktop_accessibility, has_errors, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                i + 1,
                f"https://prefeitura{i}.gov.br",
                datetime.utcnow() - timedelta(hours=i),
                0.5 + (i % 50) / 100,  # Performance varia de 0.5 a 1.0
                0.6 + (i % 40) / 100,
                0.7 + (i % 30) / 100,
                0.8 + (i % 20) / 100,
                has_error,
                "Timeout error" if has_error else None,
            ],
        )

    metrics_context["audit_count"] = count


@when('eu executar o comando "stats"')
def when_run_stats(metrics_context):
    storage = metrics_context["storage"]
    metrics = asyncio.run(storage.get_aggregated_metrics())
    metrics_context["metrics"] = metrics


@then("devo ver o total de sites auditados")
def then_total_sites(metrics_context):
    assert "total_audits" in metrics_context["metrics"]
    assert metrics_context["metrics"]["total_audits"] == metrics_context["audit_count"]


@then("devo ver a taxa de sucesso")
def then_success_rate(metrics_context):
    assert "success_rate" in metrics_context["metrics"]
    assert 0 <= metrics_context["metrics"]["success_rate"] <= 1


@then("devo ver a taxa de erros")
def then_error_rate(metrics_context):
    assert "error_rate" in metrics_context["metrics"]
    assert 0 <= metrics_context["metrics"]["error_rate"] <= 1


# ============================================================================
# Cenario: Medias de performance
# ============================================================================


@given(parsers.parse("{count:d} auditorias com scores de performance variados"))
def given_varied_performance(metrics_context, count, storage_sync):
    metrics_context["storage"] = storage_sync

    for i in range(count):
        storage_sync.conn.execute(
            """
            INSERT INTO audit_summaries (id, url, timestamp, mobile_performance, desktop_performance,
                mobile_accessibility, desktop_accessibility, has_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                i + 1,
                f"https://prefeitura{i}.gov.br",
                datetime.utcnow(),
                0.3 + (i % 70) / 100,  # 0.3 a 1.0
                0.4 + (i % 60) / 100,
                0.8,
                0.85,
                False,
            ],
        )


@when("eu solicitar as metricas agregadas")
def when_request_metrics(metrics_context):
    storage = metrics_context["storage"]
    metrics = asyncio.run(storage.get_aggregated_metrics())
    metrics_context["metrics"] = metrics


@then("devo ver a media de performance mobile")
def then_avg_mobile_perf(metrics_context):
    assert "avg_mobile_performance" in metrics_context["metrics"]
    assert metrics_context["metrics"]["avg_mobile_performance"] is not None


@then("devo ver a media de performance desktop")
def then_avg_desktop_perf(metrics_context):
    assert "avg_desktop_performance" in metrics_context["metrics"]
    assert metrics_context["metrics"]["avg_desktop_performance"] is not None


@then("devo ver o desvio padrao")
def then_std_dev(metrics_context):
    assert "std_mobile_performance" in metrics_context["metrics"]


# ============================================================================
# Cenario: Agrupar por estado
# ============================================================================


@given("auditorias de sites de diferentes estados brasileiros")
def given_audits_by_state(metrics_context, storage_sync):
    metrics_context["storage"] = storage_sync

    states = ["SP", "RJ", "MG", "BA", "RS"]
    id_counter = 1
    for i, state in enumerate(states):
        for j in range(10):
            storage_sync.conn.execute(
                """
                INSERT INTO audit_summaries (id, url, timestamp, mobile_performance, desktop_performance,
                    mobile_accessibility, desktop_accessibility, has_errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    id_counter,
                    f"https://prefeitura{j}.{state.lower()}.gov.br",
                    datetime.utcnow(),
                    0.5 + (i * 0.1),  # Estados com performance diferente
                    0.6 + (i * 0.08),
                    0.7 + (i * 0.05),
                    0.8,
                    False,
                ],
            )
            id_counter += 1


@when("eu solicitar metricas agrupadas por estado")
def when_request_by_state(metrics_context):
    storage = metrics_context["storage"]
    metrics = asyncio.run(storage.get_metrics_by_state())
    metrics_context["metrics_by_state"] = metrics


@then("devo ver a media de acessibilidade por estado")
def then_accessibility_by_state(metrics_context):
    assert metrics_context.get("metrics_by_state") is not None
    assert len(metrics_context["metrics_by_state"]) > 0


@then("devo ver o ranking de estados por performance")
def then_ranking_by_state(metrics_context):
    states = metrics_context["metrics_by_state"]
    # Verificar que esta ordenado
    perfs = [s["avg_performance"] for s in states]
    assert perfs == sorted(perfs, reverse=True)


# ============================================================================
# Cenario: Piores sites
# ============================================================================


@when(parsers.parse("eu solicitar os {count:d} piores sites"))
def when_worst_sites(metrics_context, count):
    storage = metrics_context["storage"]
    sites = asyncio.run(storage.get_worst_performing_sites(limit=count))
    metrics_context["worst_sites"] = sites


@then("devo ver uma lista ordenada por score de performance")
def then_ordered_list(metrics_context):
    sites = metrics_context.get("worst_sites", [])
    assert len(sites) > 0


@then("o primeiro da lista deve ter o menor score")
def then_first_is_worst(metrics_context):
    sites = metrics_context["worst_sites"]
    if len(sites) > 1:
        assert sites[0]["mobile_performance"] <= sites[1]["mobile_performance"]


# ============================================================================
# Cenario: Melhores sites em acessibilidade
# ============================================================================


@when(parsers.parse("eu solicitar os {count:d} melhores sites em acessibilidade"))
def when_best_accessibility(metrics_context, count):
    storage = metrics_context["storage"]
    sites = asyncio.run(storage.get_best_accessibility_sites(limit=count))
    metrics_context["best_sites"] = sites


@then("devo ver uma lista ordenada por score de acessibilidade")
def then_ordered_by_accessibility(metrics_context):
    sites = metrics_context.get("best_sites", [])
    assert len(sites) > 0


@then("o primeiro da lista deve ter o maior score")
def then_first_is_best(metrics_context):
    sites = metrics_context["best_sites"]
    if len(sites) > 1:
        assert sites[0]["mobile_accessibility"] >= sites[1]["mobile_accessibility"]


# ============================================================================
# Cenario: Exportar JSON
# ============================================================================


@given("auditorias no banco de dados")
def given_some_audits(metrics_context, storage_sync):
    metrics_context["storage"] = storage_sync

    for i in range(10):
        storage_sync.conn.execute(
            """
            INSERT INTO audit_summaries (id, url, timestamp, mobile_performance, desktop_performance,
                mobile_accessibility, desktop_accessibility, has_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                i + 1,
                f"https://prefeitura{i}.gov.br",
                datetime.utcnow(),
                0.75,
                0.80,
                0.85,
                0.90,
                False,
            ],
        )


@when("eu exportar as metricas agregadas para JSON")
def when_export_json(metrics_context, output_dir):
    storage = metrics_context["storage"]
    output_file = output_dir / "metrics.json"
    asyncio.run(storage.export_aggregated_metrics_json(output_file))
    metrics_context["output_file"] = output_file


@then("um arquivo JSON deve ser criado")
def then_json_created(metrics_context):
    assert metrics_context["output_file"].exists()


@then("deve conter as medias de todas as categorias")
def then_contains_averages(metrics_context):
    data = json.loads(metrics_context["output_file"].read_text())
    assert "avg_mobile_performance" in data
    assert "avg_mobile_accessibility" in data


@then("deve conter a data de geracao")
def then_contains_date(metrics_context):
    data = json.loads(metrics_context["output_file"].read_text())
    assert "generated_at" in data


# ============================================================================
# Cenario: Evolucao temporal
# ============================================================================


@given("auditorias de diferentes datas para o mesmo site")
def given_temporal_audits(metrics_context, storage_sync):
    metrics_context["storage"] = storage_sync
    url = "https://prefeitura-teste.gov.br"

    for i in range(30):
        # Performance melhora ao longo do tempo
        storage_sync.conn.execute(
            """
            INSERT INTO audit_summaries (id, url, timestamp, mobile_performance, desktop_performance,
                mobile_accessibility, desktop_accessibility, has_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                i + 1,
                url,
                datetime.utcnow() - timedelta(days=30 - i),
                0.5 + (i * 0.015),  # 0.5 -> 0.95
                0.6 + (i * 0.012),
                0.85,
                0.90,
                False,
            ],
        )

    metrics_context["test_url"] = url


@when("eu solicitar a evolucao temporal")
def when_request_evolution(metrics_context):
    storage = metrics_context["storage"]
    url = metrics_context["test_url"]
    evolution = asyncio.run(storage.get_temporal_evolution(url))
    metrics_context["evolution"] = evolution


@then("devo ver a variacao de performance ao longo do tempo")
def then_see_variation(metrics_context):
    evolution = metrics_context.get("evolution", [])
    assert len(evolution) > 0


@then("devo identificar tendencias de melhoria ou piora")
def then_identify_trend(metrics_context):
    evolution = metrics_context["evolution"]
    if len(evolution) > 1:
        # Verifica se consegue calcular tendencia
        first = evolution[0]["mobile_performance"]
        last = evolution[-1]["mobile_performance"]
        # Neste caso, esperamos melhoria
        assert last > first
