import argparse
import csv
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = BASE_DIR / "logs" / "processamento.jsonl"
EXECUTION_ID = uuid.uuid4().hex[:12]


def log_evento(evento: str, mensagem: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_id": EXECUTION_ID,
        "evento": evento,
        "mensagem": mensagem,
    }
    with LOG_FILE.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def carregar_alertas(api_url: str, csv_path: Path | None, tentativas: int = 3) -> list[dict]:
    if csv_path:
        if not csv_path.exists():
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")
        with csv_path.open("r", encoding="utf-8-sig", newline="") as arquivo:
            return list(csv.DictReader(arquivo))

    url = f"{api_url.rstrip('/')}/api/alertas"
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=10) as response:
                dados = json.loads(response.read().decode("utf-8"))
            break
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            ultimo_erro = exc
            log_evento(
                "TENTATIVA",
                f"Tentativa {tentativa}/{tentativas} falhou ao consultar {url}: {type(exc).__name__}.",
            )
            if tentativa < tentativas:
                time.sleep(0.5 * tentativa)
    else:
        raise ConnectionError(f"API indisponível após {tentativas} tentativas.") from ultimo_erro

    if not isinstance(dados, list):
        raise ValueError("A resposta da API não contém uma lista de alertas.")
    return dados


def calcular_prioridade(
    alerta: dict,
    limiar_alta: float = 0.85,
    limiar_media: float = 0.70,
) -> str:
    status = str(alerta.get("status", "")).upper()
    try:
        confianca = float(alerta.get("confianca", 0) or 0)
    except (TypeError, ValueError):
        confianca = 0

    if status == "PENDENTE" and confianca >= limiar_alta:
        return "ALTA"
    if status in {"PENDENTE", "CONFIRMADO"} and confianca >= limiar_media:
        return "MEDIA"
    return "BAIXA"


def processar(
    alertas: list[dict],
    limiar_alta: float = 0.85,
    limiar_media: float = 0.70,
) -> dict:
    vistos: set[str] = set()
    processados: list[dict] = []
    duplicados = 0
    invalidos = 0

    for indice, alerta in enumerate(alertas, start=1):
        evento_id = str(alerta.get("evento_id", "")).strip()
        tipo = str(alerta.get("tipo_ocorrencia", "")).strip()
        if not evento_id or not tipo:
            invalidos += 1
            log_evento("INVALIDO", "Registro ignorado por não possuir evento_id ou tipo_ocorrencia.")
            continue

        try:
            confianca = float(alerta.get("confianca", 0) or 0)
        except (TypeError, ValueError):
            invalidos += 1
            log_evento("INVALIDO", f"Evento {evento_id} possui confiança não numérica.")
            continue
        if not 0 <= confianca <= 1:
            invalidos += 1
            log_evento("INVALIDO", f"Evento {evento_id} possui confiança fora do intervalo 0 a 1.")
            continue
        if str(alerta.get("status", "")).upper() not in {"PENDENTE", "CONFIRMADO", "DESCARTADO"}:
            invalidos += 1
            log_evento("INVALIDO", f"Evento {evento_id} possui status inválido.")
            continue

        if evento_id in vistos:
            duplicados += 1
            log_evento("DUPLICADO", f"Evento {evento_id} já havia sido processado.")
            continue
        vistos.add(evento_id)

        processado = dict(alerta)
        processado["confianca"] = confianca
        processado["prioridade"] = calcular_prioridade(alerta, limiar_alta, limiar_media)
        processado["ordem_processamento"] = indice
        processados.append(processado)
        log_evento("SUCESSO", f"Evento {evento_id} processado com prioridade {processado['prioridade']}.")

    resumo = {
        "execution_id": EXECUTION_ID,
        "total_entrada": len(alertas),
        "total_processados": len(processados),
        "invalidos": invalidos,
        "duplicados": duplicados,
        "prioridades": {
            prioridade: sum(1 for item in processados if item["prioridade"] == prioridade)
            for prioridade in ("ALTA", "MEDIA", "BAIXA")
        },
        "gerado_em": datetime.now(timezone.utc).isoformat(),
    }
    resumo["alertas"] = processados
    return resumo


def salvar_resultados(resumo: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "alertas_priorizados.json"
    csv_path = OUTPUT_DIR / "alertas_priorizados.csv"

    json_temporario = json_path.with_suffix(".tmp")
    csv_temporario = csv_path.with_suffix(".tmp")
    with json_temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=2)
    json_temporario.replace(json_path)

    campos = ["evento_id", "tipo_ocorrencia", "data_evento", "confianca", "status", "prioridade"]
    with csv_temporario.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for alerta in resumo["alertas"]:
            escritor.writerow({campo: alerta.get(campo, "") for campo in campos})
    csv_temporario.replace(csv_path)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="RPA de priorização dos alertas do AlertaVida.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--tentativas", type=int, default=3)
    parser.add_argument("--limiar-alta", type=float, default=0.85)
    parser.add_argument("--limiar-media", type=float, default=0.70)
    args = parser.parse_args()

    if not 0 <= args.limiar_media <= args.limiar_alta <= 1:
        print("Erro: os limiares devem seguir 0 <= limiar_media <= limiar_alta <= 1.", file=sys.stderr)
        return 1
    if args.tentativas < 1:
        print("Erro: --tentativas deve ser pelo menos 1.", file=sys.stderr)
        return 1

    log_evento("INICIO", "Iniciando processamento dos alertas.")
    try:
        alertas = carregar_alertas(args.api_url, args.csv, args.tentativas)
        resumo = processar(alertas, args.limiar_alta, args.limiar_media)
        json_path, csv_path = salvar_resultados(resumo)
        log_evento(
            "CONCLUIDO",
            f"Processados={resumo['total_processados']} "
            f"inválidos={resumo['invalidos']} duplicados={resumo['duplicados']}.",
        )
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        print(f"\nSaídas geradas:\n- {json_path}\n- {csv_path}")
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        log_evento("ERRO", str(exc))
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
