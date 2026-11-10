from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Alerta(BaseModel):
    model_config = ConfigDict(extra="allow")

    evento_id: str
    tipo_ocorrencia: str | None = None
    data_evento: datetime | date | str | None = None
    confianca: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None
    simulado: bool = False


class Indicadores(BaseModel):
    total: int
    pendentes: int
    confirmados: int
    descartados: int
    confianca_media: float | None = None


class Estatisticas(BaseModel):
    por_tipo: dict[str, int]
    por_status: dict[str, int]
    confiancas: list[dict[str, Any]]
