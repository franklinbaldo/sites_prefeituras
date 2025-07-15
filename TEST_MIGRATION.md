# 🧪 TESTES DA MIGRAÇÃO PYTHON

Execute estes comandos para testar se a migração está funcionando:

## 1️⃣ **Verificar UV e Instalação**

```bash
cd sites_prefeituras

# Verificar se UV está instalado
uv --version

# Instalar dependências
uv sync

# Verificar se CLI foi instalada
uv run sites-prefeituras --help
```

**✅ Esperado:** Deve mostrar help do CLI com comandos audit, batch, serve, stats, cleanup

## 2️⃣ **Testar Comandos CLI**

```bash
# Testar help de cada comando
uv run sites-prefeituras audit --help
uv run sites-prefeituras batch --help
uv run sites-prefeituras serve --help
uv run sites-prefeituras stats --help
uv run sites-prefeituras cleanup --help
```

**✅ Esperado:** Cada comando deve mostrar suas opções específicas

## 3️⃣ **Testar Comando Cleanup**

```bash
# Verificar quais arquivos JS existem
uv run sites-prefeituras cleanup --remove-js
```

**✅ Esperado:** Deve listar arquivos JavaScript encontrados ou dizer que não há nenhum

## 4️⃣ **Executar Testes Python**

```bash
# Executar todos os testes
uv run pytest

# Executar apenas testes E2E
uv run pytest -m e2e

# Executar com verbose
uv run pytest -v
```

**✅ Esperado:** Testes devem passar (podem ter alguns warnings, mas não erros)

## 5️⃣ **Testar Documentação**

```bash
# Servir documentação MkDocs
uv run mkdocs serve
```

**✅ Esperado:** Deve iniciar servidor em http://localhost:8000 com docs

## 6️⃣ **Testar Comando Stats (sem API key)**

```bash
# Testar stats sem banco existente
uv run sites-prefeituras stats
```

**✅ Esperado:** Deve criar banco vazio e mostrar estatísticas zeradas

## 7️⃣ **Testar Comando Audit (sem API key)**

```bash
# Testar audit sem API key (deve falhar graciosamente)
uv run sites-prefeituras audit https://example.com
```

**✅ Esperado:** Deve mostrar erro pedindo PAGESPEED_API_KEY

## 8️⃣ **Verificar Estrutura de Arquivos**

```bash
# Verificar se arquivos Python foram criados
ls -la src/sites_prefeituras/
ls -la tests/
ls -la docs/

# Verificar pyproject.toml
cat pyproject.toml
```

**✅ Esperado:** Deve mostrar todos os arquivos Python criados

---

## 🎯 **CHECKLIST DE TESTES:**

- [ ] UV instalado e funcionando
- [ ] `uv sync` executa sem erros
- [ ] CLI `sites-prefeituras --help` funciona
- [ ] Todos os comandos têm help
- [ ] `pytest` executa (pode ter warnings)
- [ ] `mkdocs serve` funciona
- [ ] Comando `stats` cria banco vazio
- [ ] Comando `audit` pede API key
- [ ] Comando `cleanup` detecta arquivos JS
- [ ] Estrutura de arquivos Python está correta

---

## 🚨 **SE ALGO FALHAR:**

### Erro de importação:
```bash
# Verificar se pacote está instalado corretamente
uv run python -c "import sites_prefeituras; print('OK')"
```

### Erro de dependências:
```bash
# Reinstalar dependências
uv sync --reinstall
```

### Erro de testes:
```bash
# Executar teste específico
uv run pytest tests/test_cli.py::TestCLI::test_help_command -v
```

---

## 🎉 **SE TODOS OS TESTES PASSAREM:**

A migração Python está funcionando perfeitamente! ✅

Você pode:
1. Fazer o commit na branch `python-migration`
2. Configurar API key: `export PAGESPEED_API_KEY="sua_chave"`
3. Testar auditoria real: `uv run sites-prefeituras audit https://google.com`
4. Limpar arquivos JS: `uv run sites-prefeituras cleanup --remove-js --confirm`