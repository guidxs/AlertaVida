
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import csv
import urllib.request

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator


PASTA_CHEGADA = Path("/opt/airflow/chegada")

URL_ARTESP = (
    "https://dadosabertos.artesp.sp.gov.br/"
    "dataset/5e3af2a0-3b6a-4ee6-8556-b59b5d813ffc/"
    "resource/c9db7f71-2a17-4aac-a3d0-49883e61f776/"
    "download/acidentes_2025.csv"
)


def obter_data():
    return datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%Y-%m-%d")


def coletar_artesp():
    data = obter_data()
    arquivo = PASTA_CHEGADA / f"artesp_acidentes_{data}.csv"

    requisicao = urllib.request.Request(
        URL_ARTESP,
        headers={"User-Agent": "AlertaVida/1.0"}
    )

    with urllib.request.urlopen(requisicao, timeout=180) as resposta:
        conteudo = resposta.read()

    if not conteudo:
        raise ValueError("O arquivo da ARTESP está vazio.")

    arquivo.write_bytes(conteudo)

    print(f"ARTESP coletada: {arquivo}")
    print(f"Tamanho: {len(conteudo)} bytes")


def gerar_eventos():
    data = obter_data()
    arquivo = PASTA_CHEGADA / f"eventos_alertavida_{data}.csv"

    eventos = [
        {
            "evento_id": f"AV-{data}-001",
            "camera_id": "CAM-SIM-001",
            "tipo_evento": "COLISAO",
            "confianca": 0.94,
            "latitude": -23.3621,
            "longitude": -46.7405,
            "status": "PENDENTE",
            "simulado": True
        },
        {
            "evento_id": f"AV-{data}-002",
            "camera_id": "CAM-SIM-002",
            "tipo_evento": "POSSIVEL_ATROPELAMENTO",
            "confianca": 0.87,
            "latitude": -23.3650,
            "longitude": -46.7350,
            "status": "PENDENTE",
            "simulado": True
        },
        {
            "evento_id": f"AV-{data}-003",
            "camera_id": "CAM-SIM-003",
            "tipo_evento": "QUEDA_DE_MOTOCICLISTA",
            "confianca": 0.91,
            "latitude": -23.3590,
            "longitude": -46.7380,
            "status": "PENDENTE",
            "simulado": True
        }
    ]

    with arquivo.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f,
            fieldnames=eventos[0].keys()
        )
        escritor.writeheader()
        escritor.writerows(eventos)

    print(f"Eventos simulados gerados: {arquivo}")


def verificar_arquivos():
    data = obter_data()

    arquivos = [
        PASTA_CHEGADA / f"artesp_acidentes_{data}.csv",
        PASTA_CHEGADA / f"eventos_alertavida_{data}.csv"
    ]

    for arquivo in arquivos:
        if not arquivo.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {arquivo}"
            )

        if arquivo.stat().st_size == 0:
            raise ValueError(
                f"Arquivo vazio: {arquivo}"
            )

        print(
            f"OK: {arquivo.name} - "
            f"{arquivo.stat().st_size} bytes"
        )

    print("Todas as coletas foram verificadas!")


with DAG(
    dag_id="alertavida_coleta",
    description="Coleta de acidentes ARTESP e eventos simulados",
    start_date=datetime(2026, 11, 9, tzinfo=ZoneInfo("America/Sao_Paulo")),
    schedule="0 7 * * *",
    catchup=False,
    tags=["alertavida", "big-data"]
) as dag:

    tarefa_artesp = PythonOperator(
        task_id="coletar_artesp",
        python_callable=coletar_artesp
    )

    tarefa_eventos = PythonOperator(
        task_id="gerar_eventos",
        python_callable=gerar_eventos
    )

    tarefa_verificacao = PythonOperator(
        task_id="verificar_arquivos",
        python_callable=verificar_arquivos
    )

    [tarefa_artesp, tarefa_eventos] >> tarefa_verificacao
