---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
language:
- pt
tags:
- base_model:adapter:Qwen/Qwen2.5-1.5B-Instruct
- lora
- transformers
---

# AlertaVida LoRA Adapter

Adapter LoRA para o protótipo acadêmico AlertaVida. Ajusta o modelo base para
produzir saídas estruturadas de triagem em português e recusas quando a base de
conhecimento não sustenta uma resposta.

## Uso previsto

Demonstração e avaliação acadêmica com eventos sintéticos de possíveis acidentes.
A saída é uma sugestão para um operador; não confirma ocorrências, não substitui
profissionais e não aciona serviços de emergência.

## Modelo e treinamento

- Modelo base: Qwen/Qwen2.5-1.5B-Instruct.
- Método: PEFT LoRA para modelo causal de linguagem.
- Módulos-alvo: q_proj, k_proj, v_proj e o_proj.
- Configuração: r=16, alpha=32, dropout=0.05.
- Épocas: 3; taxa de aprendizado: 2e-4; batch por dispositivo: 1; acumulação: 8.
- Dados: casos sintéticos em português, descritos em avaliacao/casos_treino.jsonl.
- Parâmetros treináveis: 4.358.144 de 1.548.072.448 (0,2815%).
- Hardware do treinamento: não registrado.
- Licença do adaptador: a definir junto à licença aplicável ao modelo base e aos materiais de treinamento.

## Limitações e riscos

O conjunto de treino e os testes são pequenos, sintéticos e baseados em modelos
de texto. O adaptador pode errar, gerar JSON inválido, citar trechos inadequados
ou classificar incorretamente uma situação. Os resultados não demonstram
segurança para operação real. Use apenas em avaliação controlada e mantenha
validação humana.

## Avaliação

Consulte o README principal em `../../../README.md` e os resultados em
`../../../avaliacao/` para as métricas e limitações observadas. A licença do
modelo base e as condições de redistribuição devem ser verificadas antes de
publicar este adaptador.
### Framework versions

- PEFT 0.21.3