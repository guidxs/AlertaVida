# Relatório técnico — RPA do AlertaVida

## Identificação

- Produto: AlertaVida
- Componente: automação da triagem operacional de alertas
- Integração: API FastAPI do MVP ou CSV de demonstração
- Saídas: JSON, CSV e registro JSONL

## Problema operacional

Alertas identificados pelo MVP precisam ser organizados antes da revisão humana. O processo manual
exigiria validar campos, remover registros repetidos e separar prioridades.

## Objetivo da automação

Executar essa triagem de forma repetível, produzir evidências de auditoria e entregar arquivos estruturados
sem substituir a decisão humana nem acionamentos de emergência.

## Processo implementado

1. Selecionar fonte CSV ou API.
2. Consultar a API com até três tentativas em caso de falha transitória.
3. Percorrer a coleção de alertas.
4. Validar identificador, tipo, status e confiança.
5. Identificar eventos duplicados.
6. Aplicar os limiares de prioridade.
7. Salvar resultados JSON e CSV de forma atômica.
8. Registrar início, tentativas, sucessos, exceções e conclusão.
9. Disponibilizar o resumo no backend pela rota `/api/rpa/ultima-execucao`.

## Regras de decisão

| Condição | Resultado |
|---|---|
| PENDENTE e confiança >= 85% | ALTA |
| PENDENTE ou CONFIRMADO e confiança >= 70% | MEDIA |
| Outros casos | BAIXA |

## Resiliência

- Arquivo inexistente retorna erro controlado.
- API indisponível gera novas tentativas.
- JSON inválido da API é rejeitado.
- Campo vazio é registrado como inválido.
- Status desconhecido é registrado como inválido.
- Confiança fora de 0 a 1 é registrada como inválida.
- Evento repetido é registrado como duplicado.
- O resultado é escrito em arquivo temporário e substituído de forma completa.

## Segurança e LGPD

Não são necessários CPF, telefone, endereço pessoal ou dados médicos. Os testes usam eventos simulados.
Os logs contêm evento operacional e mensagens técnicas, sem dados sensíveis.

## Testes

O conjunto `unittest` verifica prioridade alta, prioridade média, duplicidade, confiança fora do intervalo,
valor não numérico e status desconhecido.
