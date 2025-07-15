#!/usr/bin/env python3
"""Script básico para testar se a migração Python está funcionando."""

import sys
from pathlib import Path

def test_imports():
    """Testa se os módulos podem ser importados."""
    try:
        from sites_prefeituras import __version__
        print(f"✅ sites_prefeituras importado - versão: {__version__}")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar sites_prefeituras: {e}")
        return False

def test_cli_import():
    """Testa se o CLI pode ser importado."""
    try:
        from sites_prefeituras.cli import app
        print("✅ CLI importado com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar CLI: {e}")
        return False

def test_models_import():
    """Testa se os modelos podem ser importados."""
    try:
        from sites_prefeituras.models import SiteAudit, BatchAuditConfig
        print("✅ Modelos Pydantic importados com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar modelos: {e}")
        return False

def test_collector_import():
    """Testa se o collector pode ser importado."""
    try:
        from sites_prefeituras.collector import PageSpeedCollector
        print("✅ Collector importado com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar collector: {e}")
        return False

def test_storage_import():
    """Testa se o storage pode ser importado."""
    try:
        from sites_prefeituras.storage import DuckDBStorage
        print("✅ Storage importado com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar storage: {e}")
        return False

def test_file_structure():
    """Testa se a estrutura de arquivos está correta."""
    required_files = [
        "pyproject.toml",
        "src/sites_prefeituras/__init__.py",
        "src/sites_prefeituras/cli.py",
        "src/sites_prefeituras/models.py",
        "src/sites_prefeituras/collector.py",
        "src/sites_prefeituras/storage.py",
        "tests/test_cli.py",
        "mkdocs.yml",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Arquivos faltando: {missing_files}")
        return False
    else:
        print("✅ Todos os arquivos necessários estão presentes")
        return True

def main():
    """Executa todos os testes básicos."""
    print("🧪 Testando migração Python...")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_imports,
        test_cli_import,
        test_models_import,
        test_collector_import,
        test_storage_import,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 MIGRAÇÃO PYTHON FUNCIONANDO PERFEITAMENTE!")
        return 0
    else:
        print("⚠️ Alguns testes falharam. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())