# AlertaVida — Big Data Architecture & Data Integration

## 1. Sobre a atividade

O AlertaVida é um projeto de tecnologia cidadã que busca auxiliar na identificação e organização de possíveis ocorrências no trânsito.

Nesta etapa, foi desenvolvido um pipeline de dados responsável por coletar informações, armazená-las, realizar tratamentos e disponibilizar os resultados para consumo pelo MVP.

O pipeline utiliza Apache Airflow para orquestração e Databricks para processamento e armazenamento nas camadas Bronze, Prata e Ouro.

## 2. Integrantes

- Guilherme Doretto Sobreiro — RM 99674
- Guilherme Fazito Ziolli Sordili — RM 550539

## Link do vídeo
- Mostrando o MVP: https://www.youtube.com/watch?v=lyxsTVF79Ew

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
| **URL do MVP e repositório** | MVP: http://107.21.51.139 (IP público fixo; servidor ligado por até 4 horas por sessão) · MVP local: http://localhost:5173/ · GenAI local: http://localhost:8001/ · Repositório: https://github.com/guidxs/AlertaVida |
| **Indicadores de impacto** | Quantidade de ocorrências identificadas, precisão e recall das detecções, tempo entre identificação e encaminhamento, tempo de triagem, taxa de JSON válido, citação correta das fontes e taxa de recusa quando faltam evidências. |
| **ODS conectados** | **ODS 3 — Saúde e Bem-Estar:** apoia a identificação e o encaminhamento mais rápidos de possíveis acidentes.<br>**ODS 9 — Indústria, Inovação e Infraestrutura:** aplica IA, dados e infraestrutura digital a um desafio de segurança viária.<br>**ODS 10 — Redução das Desigualdades:** busca apoiar o acesso mais equitativo à ajuda, sem depender da capacidade financeira da pessoa. |

## Adendo: disponibilidade do MVP
O MVP foi implantado por meio do AWS Academy Learner Lab, em razão dos créditos disponíveis.
Por esse motivo, o servidor permanece ligado por apenas 4 horas e depois é desligado
automaticamente, de modo que a aplicação pode estar fora do ar quando o endereço
http://107.21.51.139 for acessado. Caso queira ver a aplicação em funcionamento, basta entrar em
contato pelo Teams para que o ambiente seja ligado. A demonstração também está gravada em vídeo:
https://www.youtube.com/watch?v=lyxsTVF79Ew.

## 3. Arquitetura

O fluxo de dados foi organizado da seguinte maneira:

1. **Fontes:** coleta de dados históricos de acidentes da ARTESP e geração de registros simulados do AlertaVida.
2. **Airflow:** execução agendada das tarefas de coleta e verificação dos arquivos.
3. **Chegada:** armazenamento local dos arquivos CSV com identificação da data de coleta.
4. **Volume Databricks:** envio manual dos arquivos em lotes para o armazenamento.
5. **Bronze:** ingestão dos dados brutos utilizando `COPY INTO`.
6. **Prata:** conversão de tipos, deduplicação, validação e aplicação de regras de qualidade.
7. **Ouro:** organização dos dados em tabelas dimensionais e disponibilização das informações para o MVP.
8. **MVP:** consumo dos dados por meio de uma API Python com FastAPI e apresentação em uma interface React.

O Databricks Free Edition não possui integração direta com o Airflow utilizado neste projeto. Por isso, os arquivos são enviados manualmente ao Volume do Databricks.

## 4. Fontes de dados

### 4.1 ARTESP

Fonte externa real: [Dados Abertos da ARTESP — Acidentes](https://dadosabertos.artesp.sp.gov.br/dataset/acidentes).

Foi utilizada a base histórica de acidentes de 2025, contendo informações como data, horário, rodovia, município, condições do acidente e quantidade de vítimas.

**Observação:** como a base é histórica e estática, as duas coletas realizadas em dias diferentes possuem o mesmo conteúdo. Os arquivos são identificados pelas respectivas datas de coleta.

### 4.2 Eventos AlertaVida

A segunda fonte consiste em registros simulados de possíveis ocorrências detectadas pelo sistema AlertaVida.

Os registros representam situações como:

- Colisão.
- Possível atropelamento.
- Queda de motociclista.

Os dados incluem identificador do evento, referência da câmera, tipo de ocorrência, confiança, coordenadas geográficas, status e indicador de simulação.

Esses registros são simulados e não representam ocorrências reais.

## 5. Airflow e coleta

Foi desenvolvido um DAG chamado `alertavida_coleta`, configurado para execução diária às 07h, no fuso horário de São Paulo.

O DAG possui três etapas:

- Coleta dos dados da ARTESP.
- Geração dos eventos simulados do AlertaVida.
- Verificação da chegada dos arquivos.

As duas tarefas de coleta são executadas em paralelo. A etapa de verificação é executada após as duas coletas.

Os arquivos são armazenados na pasta `chegada/`, com a data de coleta no nome.

Exemplos:

- `artesp_acidentes_2026-11-09.csv`
- `artesp_acidentes_2026-11-10.csv`
- `eventos_alertavida_2026-11-09.csv`
- `eventos_alertavida_2026-11-10.csv`

Foram realizadas duas coletas em dias diferentes, e os respectivos arquivos foram enviados ao Volume do Databricks.

## 6. Databricks — Lakehouse

### 6.1 Bronze

A camada Bronze recebe os dados brutos por meio de comandos `COPY INTO`, utilizando arquivos CSV armazenados no Volume.

Foram carregados dois lotes:

| Fonte | Registros |
|---|---:|
| ARTESP | 88.268 |
| Eventos AlertaVida | 6 |
| **Total** | **88.274** |

A ingestão utiliza o controle de arquivos do `COPY INTO`, evitando o reprocessamento dos mesmos arquivos em execuções posteriores.

Como os dois arquivos da ARTESP contêm a mesma base histórica de 2025, os registros repetidos entre os lotes são preservados na Bronze e tratados posteriormente na Prata.

### 6.2 Prata

Na camada Prata, os dados passam por conversão de tipos, validações e tratamento de registros inválidos.

O processamento utiliza comandos `MERGE INTO`, com as seguintes chaves:

- ARTESP: `acidente_id`.
- Eventos AlertaVida: `evento_id`.

O `MERGE` utiliza a condição `WHEN NOT MATCHED THEN INSERT`, evitando a inserção de registros que já estejam presentes na tabela.

**Resultados da ARTESP:**

| Indicador | Total |
|---|---:|
| Registros após deduplicação | 44.058 |
| Datas e horários inválidos | 0 |
| Coordenadas inválidas | 1 |
| Dados essenciais inválidos | 0 |
| Registros válidos na Silver | 44.057 |

Um registro foi rejeitado por não possuir coordenadas geográficas válidas.

**Resultados dos eventos AlertaVida:**

| Indicador | Total |
|---|---:|
| Registros recebidos | 6 |
| Registros válidos | 6 |
| Registros rejeitados | 0 |

Foram aplicadas validações de identificadores, campos obrigatórios, confiança e coordenadas geográficas.

### 6.3 Ouro

A camada Ouro organiza os dados em um modelo dimensional para atender às necessidades do MVP.

Tabelas desenvolvidas:

- `gold_fato_eventos`: tabela fato com os registros dos eventos.
- `gold_dim_camera`: dimensão de câmeras.
- `gold_dim_tipo_evento`: dimensão dos tipos de ocorrência.
- `gold_dim_data`: dimensão de datas.

**Resultados:**

| Tabela | Registros |
|---|---:|
| gold_fato_eventos | 6 |
| gold_dim_camera | 3 |
| gold_dim_tipo_evento | 3 |
| gold_dim_data | 2 |

### 6.4 Consultas SQL

Foram desenvolvidas cinco consultas SQL para responder perguntas relacionadas ao funcionamento do AlertaVida e ao contexto de acidentes de trânsito:

1. **Resumo dos alertas:** quantidade total de alertas e distribuição por status.
2. **Ocorrências por tipo:** quantidade de eventos e confiança média por tipo de ocorrência.
3. **Ocorrências por câmera:** distribuição dos alertas por câmera de origem.
4. **Acidentes históricos por município:** identificação dos municípios com maior quantidade de acidentes na base da ARTESP.
5. **Análise de impacto:** comparação entre indicadores históricos de acidentes e os alertas registrados pelo AlertaVida.

A consulta de impacto identificou 524 acidentes históricos, 12 vítimas fatais e 21 vítimas graves nos municípios considerados, além de 6 alertas simulados do AlertaVida.

Os dados históricos e simulados possuem naturezas distintas. Portanto, não representam uma relação causal entre os acidentes da ARTESP e os alertas do sistema.

## 7. LGPD e proteção dos dados

A camada Ouro utiliza uma referência pseudonimizada para identificar as câmeras.

O identificador original da câmera não é disponibilizado na visão consumida pelo MVP. Em seu lugar, é aplicado um hash SHA-256.

Essa abordagem reduz a exposição direta dos identificadores, mantendo a possibilidade de relacionar os eventos provenientes da mesma câmera.

## 8. Integração com o MVP

O MVP utiliza uma API desenvolvida em Python com FastAPI para consultar a visão:

`workspace.alertavida.gold_mvp_alertas`

A visão disponibiliza:

- Identificador do evento.
- Referência pseudonimizada da câmera.
- Tipo de ocorrência.
- Data do evento.
- Nível de confiança.
- Latitude e longitude.
- Status.
- Indicador de simulação.

A interface foi desenvolvida em React e permite visualizar os alertas, consultar seus detalhes e localizar as ocorrências em um mapa.

O dashboard apresenta os seis eventos simulados registrados na camada Ouro.

## 9. Como reproduzir o pipeline

### Pré-requisitos

- Python.
- Docker Desktop.
- Apache Airflow.
- Conta no Databricks Free Edition.
- Acesso ao repositório do projeto.

### Etapa 1 — Executar o Airflow

Configure o ambiente do Airflow utilizando os arquivos disponibilizados no diretório `../airflow/`.

Inicie os serviços com Docker Compose e acesse:

`http://localhost:8080`

Localize e habilite o DAG `alertavida_coleta`.

### Etapa 2 — Executar a coleta

Execute o DAG manualmente ou aguarde seu agendamento.

Os arquivos CSV serão gerados na pasta `../airflow/chegada/`.

### Etapa 3 — Enviar os arquivos ao Databricks

No Databricks, envie os arquivos de cada lote para os respectivos diretórios do Volume:

- `/Volumes/workspace/alertavida/chegada/acidentes_artesp/`
- `/Volumes/workspace/alertavida/chegada/eventos_alertavida/`

### Etapa 4 — Executar o notebook

Abra o notebook `01_pipeline_alertavida` e execute suas células na ordem apresentada.

O notebook realiza a ingestão, o tratamento dos dados, a criação das tabelas dimensionais e a disponibilização da visão consumida pelo MVP.

### Etapa 5 — Executar o MVP

Configure as variáveis de ambiente necessárias para a conexão com o Databricks, sem compartilhar tokens ou credenciais.

Execute o backend FastAPI e o frontend React conforme as instruções de seus respectivos diretórios.

## 10. Tecnologias utilizadas

- Python
- Apache Airflow
- Docker
- Databricks Free Edition
- Apache Spark
- Delta Lake
- SQL
- FastAPI
- React
- ARTESP — Dados Abertos

## 11. Repositório

Código-fonte, DAGs, notebook e demais arquivos do projeto:

[AlertaVida — GitHub](https://github.com/guidxs/AlertaVida)
