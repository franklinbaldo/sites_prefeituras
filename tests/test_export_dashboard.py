"""Tests for export-dashboard command and dashboard JSON generation."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sites_prefeituras.models import SiteAudit, PageSpeedInsightsResult
from sites_prefeituras.storage import DuckDBStorage


@pytest.mark.asyncio
async def test_export_dashboard_empty_database(tmp_path):
    """Test exporting dashboard with empty database."""
    db_path = str(tmp_path / "test.duckdb")
    storage = DuckDBStorage(db_path)
    await storage.initialize()

    try:
        output_dir = tmp_path / "dashboard"
        output_dir.mkdir()

        stats = await storage.export_dashboard_json(output_dir)

        # Verify stats
        assert "generated_at" in stats
        assert "files" in stats
        assert "total_sites" in stats
        assert stats["total_sites"] == 0
        assert len(stats["files"]) == 6

        # Verify all 6 files were created
        expected_files = [
            "summary.json",
            "ranking.json",
            "top50.json",
            "worst50.json",
            "by-state.json",
            "quarantine.json",
        ]

        for filename in expected_files:
            filepath = output_dir / filename
            assert filepath.exists(), f"Missing file: {filename}"
            assert filepath.stat().st_size > 0, f"Empty file: {filename}"

            # Verify valid JSON
            with open(filepath) as f:
                data = json.load(f)
                assert "generated_at" in data

    finally:
        await storage.close()


@pytest.mark.asyncio
async def test_export_dashboard_creates_six_files(tmp_path):
    """Test that export-dashboard creates all 6 required JSON files."""
    db_path = str(tmp_path / "test.duckdb")
    storage = DuckDBStorage(db_path)
    await storage.initialize()

    try:
        output_dir = tmp_path / "dashboard"
        output_dir.mkdir()

        stats = await storage.export_dashboard_json(output_dir)

        # Verify 6 files are listed in stats
        assert len(stats["files"]) == 6

        # Verify all 6 required files exist and are non-empty
        required_files = [
            "summary.json",
            "ranking.json",
            "top50.json",
            "worst50.json",
            "by-state.json",
            "quarantine.json"
        ]

        for filename in required_files:
            filepath = output_dir / filename
            assert filepath.exists(), f"Required file {filename} was not created"
            assert filepath.stat().st_size > 0, f"Required file {filename} is empty"

    finally:
        await storage.close()


@pytest.mark.asyncio
async def test_export_dashboard_files_are_valid_json(tmp_path):
    """Test that all exported files are valid JSON."""
    db_path = str(tmp_path / "test.duckdb")
    storage = DuckDBStorage(db_path)
    await storage.initialize()

    try:
        output_dir = tmp_path / "dashboard"
        output_dir.mkdir()

        await storage.export_dashboard_json(output_dir)

        # Verify all files are valid JSON
        for filename in ["summary.json", "ranking.json", "top50.json", "worst50.json", "by-state.json", "quarantine.json"]:
            filepath = output_dir / filename
            with open(filepath) as f:
                data = json.load(f)  # Will raise if invalid JSON
                assert isinstance(data, dict)
                assert "generated_at" in data

    finally:
        await storage.close()
