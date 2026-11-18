"""API do módulo de IA generativa. Rodar: uvicorn api.main:app --port 8000
Variável LORA=1 para usar o adaptador treinado."""
import logging
import csv
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

from alertavida.nucleo import ADAPTADOR, Buscador, Gerador, Triagem, carregar_limiar, triar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("triage")  # logs sem dados pessoais: só id, config e decisão

app = FastAPI(title="AlertaVida - Triagem (GenAI)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["*"],
)
usar_lora = os.getenv("LORA") == "1"
config = "rag_lora" if usar_lora else "rag"
buscador, gerador, limiar = Buscador(), Gerador(ADAPTADOR if usar_lora else None), carregar_limiar()
with open(Path(__file__).resolve().parents[1] / "base" / "fontes.csv", encoding="utf-8", newline="") as f:
    _fontes = list(csv.DictReader(f))


class Evento(BaseModel):
    camera_id: str
    timestamp: str
    event_type: str
    confidence: float = Field(ge=0, le=1)
    local: Optional[str] = None
    observacao: Optional[str] = None


class PedidoTriagem(BaseModel):
    evento: Evento
    pergunta: str = "Classifique a ocorrência e indique o próximo passo do operador."


@app.get("/health")
def health():
    return {"status": "ok", "config": config, "limiar": limiar}


@app.post("/triage")
def triage(p: PedidoTriagem):
    caso = {"evento": p.evento.model_dump(exclude_none=True), "pergunta": p.pergunta}
    resp, _, achados = triar(caso, config, buscador, gerador, limiar)
    resp = resp or Triagem(recusa=True, motivo_recusa="Falha ao gerar JSON válido; encaminhar para revisão humana.")
    rid = uuid.uuid4().hex[:8]
    log.info("triage id=%s config=%s recusa=%s refs=%s", rid, config, resp.recusa, resp.referencias)
    return {"id": rid, "triagem": resp.model_dump(),
            "trechos_recuperados": [{"id": t["id"], "fonte": t["fonte"], "relevancia": round(s, 3),
                                     "url": next((f["url"] for f in _fontes if f["fonte_id"] == t.get("fonte_id")), None)}
                                    for t, s in achados],
            "aviso": "Sugestão automática. Requer validação do operador antes de qualquer encaminhamento."}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="ui")
