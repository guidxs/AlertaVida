# AlertaVida

**Monitoramento inteligente de acidentes de trânsito com apoio de inteligência artificial.**

O AlertaVida é uma solução tecnológica que propõe utilizar visão computacional e análise de dados para identificar possíveis acidentes de trânsito em sistemas de câmeras urbanas, gerar alertas e encaminhá-los às equipes responsáveis pela verificação e eventual acionamento dos serviços de emergência.

A proposta é desenvolver uma solução que possa ser integrada à infraestrutura de monitoramento de diferentes municípios, contribuindo para uma identificação mais rápida de ocorrências e um melhor encaminhamento de possíveis vítimas.

> Projeto desenvolvido para a Global Solution 2026.2 da FIAP.

## 2. Integrantes

- Guilherme Doretto Sobreiro — RM 99674
- Guilherme Fazito Ziolli Sordili — RM 550539

## O problema

Acidentes de trânsito podem passar despercebidos ou demorar a ser identificados e encaminhados às equipes responsáveis. Esse intervalo pode comprometer a agilidade na avaliação da ocorrência e no atendimento às vítimas.

O AlertaVida busca contribuir para esse cenário utilizando tecnologia para auxiliar na identificação e no encaminhamento de possíveis acidentes.

## Nossa solução

A proposta é aproveitar sistemas de câmeras já existentes nas cidades para identificar possíveis acidentes automaticamente.

O funcionamento planejado segue este fluxo:

1. **Monitoramento:** utilização de imagens provenientes de sistemas de câmeras urbanas.
2. **Identificação:** processamento das imagens por um modelo de visão computacional treinado para detectar acidentes.
3. **Geração de alerta:** registro da possível ocorrência, com informações relevantes para sua identificação.
4. **Encaminhamento:** envio do alerta para uma central ou setor responsável.
5. **Verificação humana:** análise da ocorrência pelos profissionais responsáveis.
6. **Atendimento:** caso necessário, acionamento dos serviços de emergência, como o SAMU.

A inteligência artificial atua como ferramenta de identificação e apoio. A confirmação da ocorrência e a decisão sobre o atendimento permanecem sob responsabilidade humana.

## Ficha do produto

| Campo | Descrição |
|---|---|
| **Nome do produto** | AlertaVida |
| **Cidadão e território** | Pessoas envolvidas em acidentes de trânsito em áreas urbanas, com aplicação prevista para centrais de monitoramento municipais. |
| **Problema, em uma frase** | Possíveis acidentes podem demorar para ser identificados, avaliados e encaminhados às equipes responsáveis. |
| **Proposta de valor** | Transformar sinais capturados por câmeras em alertas contextualizados, com triagem assistida por IA, referências de apoio e dados territoriais para orientar a validação humana. |
| **Arquitetura: componentes** | Câmeras e vídeos de ocorrências → modelo de visão computacional → API FastAPI do MVP → painel React/Vite → módulo GenAI com recuperação de fontes (RAG), geração e validação de JSON → Databricks SQL Warehouse, mapa, indicadores e central de triagem. |
| **Fontes de dados** | Vídeos de acidentes usados no desenvolvimento, eventos e indicadores armazenados no Databricks SQL Warehouse e base documental institucional em `base/trechos.jsonl`/`base/fontes.csv`, incluindo SAMU, legislação de trânsito, PRF e orientações de emergência. |
| **Modelos de IA utilizados** | YOLO11n personalizado para detecção de acidentes; Qwen/Qwen2.5-1.5B-Instruct para geração local; `intfloat/multilingual-e5-small` para busca semântica; adaptador LoRA opcional para a configuração RAG + LoRA. |
| **URL do MVP e repositório** | MVP local: http://localhost:5173/ · GenAI local: http://localhost:8001/ · Repositório: https://github.com/guidxs/AlertaVida |
| **Indicadores de impacto** | Quantidade de ocorrências identificadas, precisão e recall das detecções, tempo entre identificação e encaminhamento, tempo de triagem, taxa de JSON válido, citação correta das fontes e taxa de recusa quando faltam evidências. |
| **ODS conectados** | **ODS 3 — Saúde e Bem-Estar:** apoia a identificação e o encaminhamento mais rápidos de possíveis acidentes.<br>**ODS 9 — Indústria, Inovação e Infraestrutura:** aplica IA, dados e infraestrutura digital a um desafio de segurança viária.<br>**ODS 10 — Redução das Desigualdades:** busca apoiar o acesso mais equitativo à ajuda, sem depender da capacidade financeira da pessoa. |

## Arquitetura e tecnologias

O AlertaVida integra componentes desenvolvidos em diferentes disciplinas:

### Big Data

Responsável pela coleta, organização e processamento de dados relacionados ao trânsito.

- Apache Airflow
- Databricks
- Python
- Processamento em camadas Bronze, Silver e Gold

### Visão Computacional

Responsável pelo desenvolvimento e treinamento do modelo de inteligência artificial para identificação de acidentes em vídeos.

- Python
- YOLO11n
- Ultralytics
- OpenCV
- PyTorch

### Desenvolvimento do MVP

Responsável pela aplicação web, API e apresentação das informações, ocorrências, indicadores e vídeos processados.

- React
- Vite
- FastAPI
- Python

### Secure DevOps Tools & Cloud Computing

Responsável pela infraestrutura em nuvem, conteinerização, automação de verificações de segurança, implantação e observabilidade.

- AWS EC2
- Docker e Docker Compose
- Terraform
- GitHub Actions
- Gitleaks
- Semgrep
- Trivy
- Prometheus
- Grafana

## Indicadores e resultados

O desenvolvimento do MVP já apresenta resultados técnicos que permitem avaliar seus componentes.

**Visão Computacional**

| Métrica | Resultado |
|---|---:|
| Precisão | 88,70% |
| Recall | 87,84% |
| mAP@50 | 92,58% |
| mAP@50-95 | 69,21% |

**Processamento de dados**

| Indicador | Resultado |
|---|---:|
| Registros na camada Bronze | 44.134 |
| Registros na camada Silver | 44.133 |

Esses resultados representam a avaliação técnica dos componentes desenvolvidos. Indicadores operacionais, como tempo de detecção, encaminhamento de alertas e atendimento às vítimas, poderão ser medidos em uma futura integração com sistemas reais de monitoramento.

## Ecossistema

A solução prevê a participação de diferentes agentes:

- **Cidadãos:** beneficiários da melhoria na identificação e no encaminhamento de acidentes.
- **Prefeituras:** responsáveis pela infraestrutura e gestão dos sistemas municipais de monitoramento.
- **Centrais de monitoramento:** responsáveis por receber e verificar os alertas.
- **Órgãos de trânsito:** envolvidos na gestão e no atendimento de ocorrências viárias.
- **Serviços de emergência:** como o SAMU, responsáveis pelo atendimento às vítimas quando necessário.

## Objetivos de Desenvolvimento Sustentável (ODS)

O AlertaVida está conectado à Agenda 2030 da Organização das Nações Unidas, principalmente aos seguintes objetivos:

### ODS 3 – Saúde e Bem-Estar

Contribui para a Meta 3.6, relacionada à redução de mortes e lesões causadas por acidentes de trânsito, ao propor mecanismos que auxiliem na identificação e no encaminhamento mais ágil de possíveis ocorrências.

### ODS 11 – Cidades e Comunidades Sustentáveis

Relaciona-se à Meta 11.2, que busca promover sistemas de transporte mais seguros e acessíveis. A proposta utiliza a infraestrutura de monitoramento urbano como ferramenta de apoio à segurança viária.

### ODS 9 – Indústria, Inovação e Infraestrutura

Aplica tecnologias como inteligência artificial, Big Data e computação em nuvem para desenvolver uma solução tecnológica que possa ser adaptada a diferentes infraestruturas municipais.

A contribuição do projeto é tecnológica e informacional, não substituindo os serviços de emergência, a fiscalização ou os órgãos responsáveis pela gestão do trânsito.

## Documentação por disciplina

- [Desenvolvimento do MVP](./mvp/README.md)
- [Big Data](./big-data/databricks/README_BIG_DATA.md)
- [Visão Computacional](./computer-vision/README.md)
- [Secure DevOps Tools & Cloud Computing](./DevOps-Cloud/ops/README.md)

Documentação complementar da infraestrutura e observabilidade:

- [Terraform](./DevOps-Cloud/infra/terraform/README.md)
- [Observabilidade com Prometheus e Grafana](./DevOps-Cloud/ops/observability/README.md)

---

**AlertaVida · FIAP Global Solution 2026.2**