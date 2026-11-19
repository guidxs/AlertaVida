# PDD — Priorização operacional de alertas

## Início

O processo começa pela definição da fonte: API do MVP ou CSV de demonstração.

## Entradas

- Lista de alertas da API `/api/alertas`.
- Alternativamente, arquivo CSV com `evento_id`, `tipo_ocorrencia`, `data_evento`, `confianca` e `status`.

## Processamento

1. Ler a coleção de alertas.
2. Para cada alerta:
   - validar campos obrigatórios;
   - verificar duplicidade pelo `evento_id`;
   - calcular prioridade pela decisão baseada em status e confiança;
   - registrar sucesso ou a falha apropriada.
3. Gerar JSON e CSV.
4. Encerrar com resumo da execução.

## Regras de decisão

- PENDENTE + confiança >= 0,85: ALTA.
- PENDENTE ou CONFIRMADO + confiança >= 0,70: MEDIA.
- Demais combinações: BAIXA.

## Exceções

- Arquivo CSV inexistente: interromper e registrar erro.
- API indisponível ou resposta inválida: interromper e registrar erro.
- Campo obrigatório vazio: ignorar registro e registrar invalidez.
- Evento duplicado: ignorar a segunda ocorrência e registrar duplicidade.
- Confiança inválida: considerar 0 e aplicar a prioridade BAIXA.

## Saídas e auditoria

- JSON estruturado consumido por outro componente.
- CSV organizado para demonstração ou consulta.
- JSONL com data/hora, evento e mensagens sem dados pessoais.
