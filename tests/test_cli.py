"""Testes E2E para a interface CLI."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from sites_prefeituras.cli import app

runner = CliRunner()


class TestCLI:
    """Testes E2E para comandos CLI."""

    def test_help_command(self):
        """Testa se o comando help funciona."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sites-prefeituras" in result.stdout
        assert "Auditoria automatizada" in result.stdout

    def test_audit_command_help(self):
        """Testa help do comando audit."""
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        assert "URL do site para auditar" in result.stdout

    def test_batch_command_help(self):
        """Testa help do comando batch."""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "Arquivo CSV com URLs" in result.stdout

    def test_serve_command_help(self):
        """Testa help do comando serve."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Porta do servidor" in result.stdout

    def test_stats_command_help(self):
        """Testa help do comando stats."""
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "estatísticas" in result.stdout.lower()

    def test_cleanup_command_help(self):
        """Testa help do comando cleanup."""
        result = runner.invoke(app, ["cleanup", "--help"])
        assert result.exit_code == 0
        assert "JavaScript" in result.stdout

    def test_audit_without_api_key(self):
        """Testa comando audit sem API key configurada."""
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(app, ["audit", "https://example.com"])
            assert result.exit_code == 1
            assert "PAGESPEED_API_KEY" in result.stdout

    def test_batch_file_not_found(self):
        """Testa comando batch com arquivo inexistente."""
        with patch.dict(os.environ, {"PAGESPEED_API_KEY": "test_key"}):
            result = runner.invoke(app, ["batch", "arquivo_inexistente.csv"])
            assert result.exit_code == 1
            assert "nao encontrado" in result.stdout

    @pytest.mark.e2e
    def test_cleanup_no_options(self):
        """Testa comando cleanup sem opções."""
        result = runner.invoke(app, ["cleanup"])
        assert result.exit_code == 0
        assert "Use --remove-js" in result.stdout

    @pytest.mark.e2e
    def test_cleanup_no_js_files(self):
        """Testa cleanup quando não há arquivos JS."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("pathlib.Path.cwd", return_value=Path(temp_dir)),
        ):
            result = runner.invoke(app, ["cleanup", "--remove-js", "--confirm"])
            assert result.exit_code == 0
            assert "Nenhum arquivo JavaScript encontrado" in result.stdout

    @pytest.mark.e2e
    def test_serve_command(self):
        """Testa comando serve."""
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        assert "Iniciando servidor" in result.stdout
        assert "ainda não implementado" in result.stdout


class TestBatchCSV:
    """Testes para processamento de CSV."""

    def test_batch_with_valid_csv(self):
        """Testa batch com CSV válido."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("url\n")
            f.write("https://example.com\n")
            f.write("https://google.com\n")
            csv_file = f.name

        try:
            with patch.dict(os.environ, {"PAGESPEED_API_KEY": "test_key"}):
                # Teste apenas se o arquivo é encontrado (não executa auditoria real)
                result = runner.invoke(
                    app,
                    [
                        "batch",
                        csv_file,
                        "--output-dir",
                        "/tmp/test_output",
                        "--max-concurrent",
                        "1",
                        "--requests-per-second",
                        "0.1",
                    ],
                )
                # Pode falhar na execução real, mas não deve falhar por arquivo não encontrado
                assert "não encontrado" not in result.stdout
        finally:
            Path(csv_file).unlink()


class TestModels:
    """Testes para modelos Pydantic."""

    def test_site_audit_creation(self):
        """Testa criação de SiteAudit."""
        from sites_prefeituras.models import SiteAudit

        audit = SiteAudit(url="https://example.com")
        assert str(audit.url) == "https://example.com/"
        assert audit.error_message is None
        assert audit.retry_count == 0

    def test_batch_audit_config_creation(self):
        """Testa criação de BatchAuditConfig."""
        from sites_prefeituras.models import BatchAuditConfig

        config = BatchAuditConfig(csv_file="test.csv")
        assert config.csv_file == "test.csv"
        assert config.output_dir == "./output"
        assert config.max_concurrent == 10
        assert config.requests_per_second == 3.5


class TestStorage:
    """Testes para sistema de storage."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_duckdb_storage_initialization(self):
        """Testa inicialização do DuckDB storage."""
        from sites_prefeituras.storage import DuckDBStorage

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.duckdb"
            storage = DuckDBStorage(str(db_path))

            await storage.initialize()
            assert storage.conn is not None

            # Verificar se tabelas foram criadas
            tables = storage.conn.execute("SHOW TABLES").fetchall()
            table_names = [table[0] for table in tables]
            assert "audits" in table_names
            assert "audit_summaries" in table_names

            await storage.close()


@pytest.mark.e2e
class TestIntegration:
    """Testes de integração E2E."""

    def test_full_cli_workflow(self):
        """Testa workflow completo do CLI."""
        # 1. Help funciona
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # 2. Comandos individuais têm help
        for command in ["audit", "batch", "serve", "stats", "cleanup"]:
            result = runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0

        # 3. Cleanup sem arquivos JS
        result = runner.invoke(app, ["cleanup", "--remove-js", "--confirm"])
        assert result.exit_code == 0
