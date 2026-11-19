# AlertaVida — Visão computacional

Esta pasta reúne o treinamento do detector de acidentes, ferramentas de validação e scripts históricos de processamento de vídeos. 

## Integrantes

- Guilherme Doretto Sobreiro — RM 99674
- Guilherme Fazito Ziolli Sordili — RM 550539

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

## Estrutura

- `src/train.py`: treinamento customizado a partir dos pesos base.
- `models/yolo11n.pt`: checkpoint base YOLO11n usado no treinamento.
- `assets/samples/`: imagens de exemplo auxiliares, incluindo `bus.jpg`.
- `dataset/processed_clean/Accident_Detection/Dataset/`: dataset preparado e `data.yaml`.
- `tools/validation/`: análises do dataset/modelo e folhas de revisão.
- `tools/video_processing/`: scripts reproduzíveis de processamento de lotes históricos.
- `tools/archive/`: utilitários de preparação/teste antigos; estão preservados para referência e não fazem parte do fluxo atual.
- `videos/gallery/`: manifesto e vídeos publicados na galeria do dashboard.
- `runs/`: resultados históricos e novos treinamentos, incluindo métricas, gráficos, matrizes de confusão, checkpoints e saídas de processamento.

Os resultados históricos estão organizados em `computer-vision/runs/`. A execução principal está em `runs/detect/runs/alertavida_yolo11n/`, e as avaliações estão em `runs/detect/results/`.

## Origem do dataset

O projeto utiliza o dataset **Accident** (https://www.kaggle.com/datasets/picekl/accident/data)

### Baixar e extrair

1. No PowerShell, a partir de `computer-vision/`, crie a pasta local para o arquivo original:

```powershell
New-Item -ItemType Directory -Force .\dataset\raw | Out-Null
```

2. Na página oficial, use **Download All** e salve o ZIP como `Accident_Detection.zip` em `computer-vision/dataset/raw/`. Essa pasta e o dataset são locais e estão excluídos do Git.
3. Ainda a partir de `computer-vision/`, extraia o ZIP para `dataset/processed_clean/`:

```powershell
Expand-Archive -LiteralPath .\dataset\raw\Accident_Detection.zip -DestinationPath .\dataset\processed_clean
```

4. Confira que o layout extraído é `dataset/processed_clean/Accident_Detection/Dataset/`, com `train/`, `valid/`, `test/` e `data.yaml`. Se a exportação trouxer uma linha `path:` apontando para uma máquina ou diretório externo, remova essa linha: o YAML deste projeto usa caminhos relativos à própria pasta do arquivo. O conteúdo esperado é:

```yaml
train: train/images
val: valid/images
test: test/images

nc: 1
names:
  0: Accident
task: detect
```

Verifique as pastas e exiba o YAML no PowerShell:

```powershell
$dataset = ".\dataset\processed_clean\Accident_Detection\Dataset"
foreach ($item in @("data.yaml", "train/images", "valid/images", "test/images")) {
    $path = Join-Path $dataset $item
    if (-not (Test-Path -LiteralPath $path)) { throw "Não encontrado: $path" }
    Write-Host "OK: $path"
}
Get-Content (Join-Path $dataset "data.yaml")
```

O treinamento usa o YOLO11n pré-treinado como ponto de partida, o dataset preparado localmente acima e os pesos base em `computer-vision/models/yolo11n.pt`. A execução padrão grava os resultados em `computer-vision/runs/detect/runs/alertavida_yolo11n/`, que também é o local padrão de `weights/best.pt` usado pelos scripts de processamento e validação.

## Ambiente Python e dependências

O ambiente inspecionado usa Python 3.11.9. As dependências Python da visão computacional estão fixadas em `requirements.txt`. PyTorch e Torchvision ficam fora desse arquivo para que a instalação CUDA seja explícita e compatível com o ambiente usado.

No PowerShell, a partir desta pasta, crie um ambiente virtual e instale primeiro as wheels CUDA de PyTorch/Torchvision:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu132
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print('CUDA disponível:', torch.cuda.is_available())"
```

Não é necessário ativar o ambiente com `Activate.ps1`; chamar diretamente o `python.exe` evita problemas de política de execução do PowerShell. O comando CUDA acima corresponde à combinação observada no ambiente analisado. O uso de CUDA também depende de GPU NVIDIA e driver compatível; sem CUDA, o treinamento configurado em `device=0` não inicia.

## Dataset e portabilidade

O arquivo `dataset/processed_clean/Accident_Detection/Dataset/data.yaml` não define uma raiz `path`. Na versão instalada do Ultralytics, quando `path` não é definido, a raiz é derivada do diretório do próprio YAML (`yaml_file.parent`). Como as divisões estão em `train/images`, `valid/images` e `test/images`, os caminhos ficam relativos à pasta real do dataset e não à pasta atual do terminal. A chave de validação é `val`, apontando para `valid/images`.

`src/train.py` resolve seus caminhos padrão relativamente à raiz `computer-vision/`, valida que o YAML e os pesos base existem e passa o caminho absoluto do YAML ao Ultralytics. Caminhos relativos informados por `--data`, `--model` ou `--project` também são resolvidos desde essa raiz. Para usar outro dataset ou checkpoint, informe caminhos absolutos ou relativos ao diretório `computer-vision/`.

## Treinamento

O treinamento não é executado ao instalar as dependências. Quando autorizado, a partir desta pasta:

```powershell
.\.venv\Scripts\python.exe .\src\train.py
```

Para executar a partir de outra pasta, indique a pasta `computer-vision` do clone e use os caminhos absolutos resolvidos localmente; os padrões continuam relativos ao projeto:

```powershell
$cvRoot = (Resolve-Path "<caminho-do-clone>\computer-vision").Path
& "$cvRoot\.venv\Scripts\python.exe" "$cvRoot\src\train.py"
```

Parâmetros disponíveis:

```powershell
.\.venv\Scripts\python.exe .\src\train.py --data "dataset\processed_clean\Accident_Detection\Dataset\data.yaml" --model "models\yolo11n.pt" --project "runs\detect\runs" --name "alertavida_yolo11n"
```

Por padrão, os novos resultados são gravados em `computer-vision/runs/detect/runs/alertavida_yolo11n/`. O script usa `exist_ok=False`, portanto não reutiliza nem sobrescreve uma execução existente. Se essa pasta já existir, escolha outro `--name`; nesse caso, defina `ALERTAVIDA_MODEL_PATH` para o `weights/best.pt` da nova execução antes de usar os scripts de processamento e validação.

## Pesos customizados para ferramentas

Os scripts de análise e processamento procuram por padrão o checkpoint em `runs/detect/runs/alertavida_yolo11n/weights/best.pt`, relativo à raiz `computer-vision/`. Para conferir se ele existe sem carregar o modelo ou executar inferência, rode a partir de `computer-vision/`:

```powershell
$checkpoint = ".\runs\detect\runs\alertavida_yolo11n\weights\best.pt"
if (Test-Path -LiteralPath $checkpoint -PathType Leaf) {
    (Resolve-Path -LiteralPath $checkpoint).Path
} else {
    throw "Checkpoint não encontrado: $checkpoint"
}
```

Para usar outro checkpoint, `ALERTAVIDA_MODEL_PATH` aceita um caminho relativo a `computer-vision/` ou absoluto. Exemplo para uma nova execução:

```powershell
$env:ALERTAVIDA_MODEL_PATH = ".\runs\detect\runs\<nome-da-execucao>\weights\best.pt"
```

Os scripts usam caminhos de dados e saída derivados da localização do próprio arquivo; não precisam ser chamados a partir de `computer-vision/`. Os scripts em `tools/archive/` são históricos e alguns podem preparar ou substituir saídas se forem executados. Revise o código e os destinos antes de usá-los.

## Ferramentas de validação

`tools/validation/` contém verificações de duplicatas, inspeções de exemplos negativos, revisão visual do dataset, análise de confiança e geração de contact sheets. As análises que usam o detector também precisam dos pesos customizados e de GPU CUDA, exceto quando o próprio script permite ajustar o dispositivo.

`tools/video_processing/` contém processadores de lotes e o reprocessador de três vídeos. Eles executam inferência e gravam arquivos de saída; use-os somente ao reproduzir essas análises e confira o destino antes de iniciar. Esta organização não executa nenhum deles.

Os vídeos de entrada não são distribuídos no repositório. Para reproduzir o processamento, obtenha os arquivos de entrada com autorização, coloque-os nas pastas locais indicadas e execute a partir de `computer-vision/`:

| Script | Entrada local | Saída local | Configuração |
| --- | --- | --- | --- |
| `tools/video_processing/process_candidates.py` | `videos/candidates/` | `videos/candidates_output/` | `conf=0.50`, CUDA 0, `imgsz=640` |
| `tools/video_processing/process_candidates_batch2.py` | `videos/candidates_batch2/` | `videos/candidates_batch2_output/` | `conf=0.50`, CUDA 0, `imgsz=640` |
| `tools/video_processing/reprocess_first_round_review.py` | `videos/candidates/` | `videos/first_round_review_conf070/` | `conf=0.70`, CUDA 0, `imgsz=640` |

Exemplo de execução, sem ativar o ambiente virtual:

```powershell
.\.venv\Scripts\python.exe .\tools\video_processing\process_candidates.py
```

Os outros dois scripts podem ser executados pelo mesmo padrão, substituindo o nome do arquivo. O processamento gera métricas e vídeos; os arquivos de entrada e os resultados locais não fazem parte do clone público. Os utilitários em `tools/archive/` são históricos e podem gravar ou substituir saídas; revise seus destinos e dependências antes de executá-los.

## Resultados e limitações

As métricas abaixo são os valores finais da partição de validação, registrados na época 80 em `runs/detect/runs/alertavida_yolo11n/results.csv`. Elas **não são métricas de um teste independente**:

| Precision | Recall | mAP50 | mAP50-95 |
| ---: | ---: | ---: | ---: |
| 0,88695 | 0,87838 | 0,92575 | 0,69207 |

![Curvas do treinamento](runs/detect/runs/alertavida_yolo11n/results.png)

O gráfico acompanha as perdas e as métricas ao longo das épocas.

![Curva Precision-Recall](runs/detect/results/test_evaluation/BoxPR_curve.png)

A curva mostra como precisão e recall variam conforme o limiar de confiança muda. Ela ajuda a visualizar o compromisso entre encontrar mais acidentes e reduzir falsos positivos.

As duas últimas imagens estão armazenadas em `runs/detect/results/test_evaluation/`. 

O modelo é um detector customizado para a classe `Accident`; seus resultados podem incluir falsos positivos ou deixar de detectar colisões. A galeria é uma demonstração com vídeos gravados.
