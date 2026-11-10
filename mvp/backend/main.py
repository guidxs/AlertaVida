from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .databricks import clear_alertas_cache, fetch_alertas
from .schemas import Alerta, Estatisticas, Indicadores


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="AlertaVida API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def load_alertas() -> list[dict]:
    try:
        return fetch_alertas()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível consultar a fonte Databricks.") from exc


@app.get("/api/health")
def health() -> dict:
    try:
        rows = load_alertas()
        return {"status": "connected", "source": "Databricks SQL Warehouse", "total": len(rows)}
    except HTTPException:
        return {"status": "disconnected", "source": "Databricks SQL Warehouse"}


@app.get("/api/alertas", response_model=list[Alerta])
def alertas(status: str | None = None, tipo: str | None = None, busca: str | None = None) -> list[dict]:
    rows = load_alertas()
    if status:
        rows = [row for row in rows if str(row.get("status", "")).casefold() == status.casefold()]
    if tipo:
        rows = [row for row in rows if str(row.get("tipo_ocorrencia", "")).casefold() == tipo.casefold()]
    if busca:
        rows = [row for row in rows if busca.casefold() in str(row.get("evento_id", "")).casefold()]
    return rows


@app.get("/api/indicadores", response_model=Indicadores)
def indicadores() -> dict:
    rows = load_alertas()
    statuses = Counter(str(row.get("status", "")).upper() for row in rows)
    confidences = [float(row["confianca"]) for row in rows if row.get("confianca") is not None]
    return {
        "total": len(rows),
        "pendentes": statuses["PENDENTE"],
        "confirmados": statuses["CONFIRMADO"],
        "descartados": statuses["DESCARTADO"],
        "confianca_media": sum(confidences) / len(confidences) if confidences else None,
    }


@app.get("/api/alertas/estatisticas", response_model=Estatisticas)
def estatisticas() -> dict:
    rows = load_alertas()
    return {
        "por_tipo": dict(Counter(str(row.get("tipo_ocorrencia") or "Sem categoria") for row in rows)),
        "por_status": dict(Counter(str(row.get("status") or "Sem status") for row in rows)),
        "confiancas": [
            {"evento_id": row.get("evento_id"), "confianca": row.get("confianca")}
            for row in rows if row.get("confianca") is not None
        ],
    }


@app.post("/api/refresh", status_code=200)
def refresh() -> dict:
    clear_alertas_cache()
    rows = load_alertas()
    return {"updated_at": datetime.now(timezone.utc).isoformat(), "total": len(rows)}
