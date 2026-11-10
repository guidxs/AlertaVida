# AlertaVida — central de monitoramento

Aplicação web com frontend React + Vite e API Python + FastAPI. O Databricks SQL Warehouse permanece como fonte oficial dos alertas; o navegador acessa somente a API local.

> Os registros atuais estão marcados como simulados. Eles não representam acidentes reais e a aplicação não aciona serviços de emergência.

## Requisitos

- Python 3.11 ou superior
- Node.js 20 ou superior e npm
- Credenciais e Warehouse Databricks no `.env` existente na raiz de `mvp`

O `.env` deve conter `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH` e `DATABRICKS_TOKEN`. O backend lê esse arquivo diretamente; os valores não são enviados ao frontend.

## Executar o backend

No PowerShell, a partir de `mvp`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Esses comandos não exigem ativar o ambiente virtual, então também funcionam quando a política do PowerShell bloqueia scripts `.ps1`.

A API fica em `http://localhost:8000`; documentação interativa em `http://localhost:8000/docs`. `GET /api/health` verifica a conexão com Databricks; `/api/alertas`, `/api/indicadores` e `/api/alertas/estatisticas` fornecem os dados usados pela interface. `POST /api/refresh` limpa o cache em memória e busca novamente na origem.

Para outro endereço de frontend, defina `CORS_ORIGINS` no ambiente do backend como uma lista separada por vírgulas.

## Executar o frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. O endereço padrão da API é `http://localhost:8000`; para alterá-lo, crie `frontend/.env.local` com `VITE_API_URL=http://localhost:8000` e reinicie o Vite.

Gerar a versão de produção:

```powershell
npm run build
npm run preview
```

## Dados e mapa

Os alertas vêm de `workspace.alertavida.gold_mvp_alertas`. O mapa usa somente latitude e longitude retornadas pela consulta. A camada cartográfica usa os tiles públicos padrão do OpenStreetMap, com filtro visual escuro no cliente e atribuição visível aos contribuidores. Use os tiles de forma interativa normal; não faça pré-carregamento em massa. Gráficos e indicadores são calculados a partir dos registros consultados, sem dados inventados.
