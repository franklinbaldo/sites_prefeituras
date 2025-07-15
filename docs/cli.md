# Uso CLI

## Coleta de Dados

Para iniciar a coleta de dados, execute o seguinte comando:

```bash
node collector/collect-psi.js
```

## Geração de JSON

Para gerar o arquivo JSON para visualização, execute:

```bash
python src/psi_auditor/generate_viewable_json.py data/psi_results.duckdb data/psi-latest-viewable-results.json
```

## Upload para o Internet Archive

Para fazer o upload do banco de dados para o Internet Archive, execute:

```bash
python src/psi_auditor/upload_to_ia.py
```
