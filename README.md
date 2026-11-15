# AlertaVida

**Monitoramento inteligente de acidentes de trânsito com apoio de inteligência artificial.**

O AlertaVida é uma solução tecnológica que propõe utilizar visão computacional e análise de dados para identificar possíveis acidentes de trânsito em sistemas de câmeras urbanas, gerar alertas e encaminhá-los às equipes responsáveis pela verificação e eventual acionamento dos serviços de emergência.

A proposta é desenvolver uma solução que possa ser integrada à infraestrutura de monitoramento de diferentes municípios, contribuindo para uma identificação mais rápida de ocorrências e um melhor encaminhamento de possíveis vítimas.

> Projeto desenvolvido para a Global Solution 2026.2 da FIAP.

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

## Ficha técnica do MVP

| Campo | Descrição |
|---|---|
| **Nome do produto** | AlertaVida |
| **Cidadão e território** | Vítimas de acidentes de trânsito em áreas urbanas, com possibilidade de aplicação em municípios de diferentes portes. |
| **Problema** | A demora na identificação e no encaminhamento de acidentes pode prejudicar a agilidade no atendimento às vítimas. |
| **Proposta de valor** | Utilizar visão computacional para identificar possíveis acidentes em câmeras urbanas, gerar alertas e encaminhá-los às equipes responsáveis pela verificação. |
| **Arquitetura** | Aplicação web, API, pipeline de dados, modelo de visão computacional, infraestrutura em nuvem e monitoramento. |
| **Fontes de dados** | Dados de ocorrências de trânsito da ARTESP e conjunto de vídeos AccidentDetection-9k, utilizado no desenvolvimento do modelo. |
| **Modelos de IA utilizados** | YOLO11n personalizado para detecção de acidentes em vídeos. |
| **URL do MVP** |  |
| **Repositório** | https://github.com/guidxs/AlertaVida |
| **Indicadores de impacto** | Quantidade de ocorrências identificadas, taxa de detecções corretas, tempo de geração e encaminhamento de alertas e tempo de verificação. |
| **ODS conectados** | ODS 3, ODS 11 e ODS 9. |

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
- [Big Data](./databricks/README.md)
- [Visão Computacional](./computer-vision/README.md)
- [Secure DevOps Tools & Cloud Computing](./ops/README.md)

Documentação complementar da infraestrutura e observabilidade:

- [Terraform](./infra/terraform/README.md)
- [Observabilidade com Prometheus e Grafana](./ops/observability/README.md)

---

**AlertaVida · FIAP Global Solution 2026.2**