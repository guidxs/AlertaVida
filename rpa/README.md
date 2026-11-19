# RPA — Priorização de alertas do AlertaVida

## Objetivo

Este componente automatiza a triagem operacional dos alertas produzidos pelo MVP do AlertaVida.
Ele recebe os dados pela API pública do projeto ou por um CSV de demonstração, valida os registros,
aplica uma regra de prioridade, remove duplicados e gera arquivos estruturados que podem ser consumidos
por outros componentes do MVP.

A implementação cobre ponta a ponta: definição da fonte, repetição em lote, regras de decisão,
reconhecimento de duplicidades, validação de dados, novas tentativas em falhas da API, logs estruturados,
gravação segura dos resultados e integração de leitura pelo próprio backend do MVP.

Nenhum dado é enviado a terceiros. Eventos reais não são acionados e não há dados pessoais nos testes.

## Fluxo

1. Iniciar o processamento.
2. Ler os alertas da API ou do CSV.
3. Percorrer cada registro.
4. Validar `evento_id` e `tipo_ocorrencia`.
5. Ignorar registro inválido e registrar o motivo.
6. Detectar `evento_id` duplicado.
7. Classificar prioridade pela combinação de status e confiança.
8. Gerar JSON, CSV e arquivo de auditoria.

O backend expõe `GET /api/rpa/ultima-execucao`, permitindo que o resultado seja consumido pela solução
integrada em `http://localhost:8000/api/rpa/ultima-execucao`.

## Regras de prioridade

- **ALTA:** status PENDENTE e confiança maior ou igual a 85%.
- **MEDIA:** PENDENTE ou CONFIRMADO e confiança maior ou igual a 70%.
- **BAIXA:** demais casos.

## Executar com CSV de demonstração

Instale a dependência de geração do relatório técnico:

```powershell
.\mvp\.venv\Scripts\python.exe -m pip install -r rpa\requirements.txt
```

```powershell
python rpa\src\processar_alertas.py --csv rpa\data\alertas_exemplo.csv
```

## Executar integrado à API

Com o backend ativo em `http://localhost:8000`:

```powershell
python rpa\src\processar_alertas.py --api-url http://localhost:8000
```

O fallback por CSV permite demonstrar o componente mesmo sem credenciais ou acesso ao Databricks.

Em caso de indisponibilidade temporária da API, o processo realiza até três tentativas com intervalo
progressivo. Arquivos JSON e CSV são escritos primeiro em arquivos temporários e substituídos somente
quando completos, evitando resultados parciais.

## Evidências e documentação

- [PDD detalhado](docs/PDD.md)
- [Fluxo BPMN](docs/FLUXO.bpmn.md)
- [Relatório técnico](docs/RELATORIO_TECNICO.md)
- [Relatório técnico em PDF](docs/Relatorio_Tecnico_RPA.pdf)

## Saídas

- `rpa/output/alertas_priorizados.json`
- `rpa/output/alertas_priorizados.csv`
- `rpa/logs/processamento.jsonl`

## Testes

```powershell
python rpa\tests\test_processar_alertas.py
```

Para gerar o PDF a partir da última execução:

```powershell
.\mvp\.venv\Scripts\python.exe rpa\src\gerar_relatorio.py
```
