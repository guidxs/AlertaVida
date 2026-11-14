from datetime import date, datetime
from functools import lru_cache
import math
import re
import unicodedata
from typing import Any

from databricks import sql

from .config import get_settings

QUERY = """
SELECT *
FROM workspace.alertavida.gold_mvp_alertas
ORDER BY data_evento DESC
"""

PUBLIC_COLUMNS = {
    "evento_id", "tipo_ocorrencia", "data_evento", "confianca",
    "latitude", "longitude", "status", "simulado",
}
CAMERA_COLUMNS = {
    "camera", "cameraid", "idcamera", "identificacaocamera",
    "identificadorcamera", "cameraidentificacao", "cameranome",
    "nomecamera", "sourcecamera", "origemcamera", "codigocamera",
}


def _is_public_column(name: str) -> bool:
    normalized = unicodedata.normalize("NFD", name.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    return name in PUBLIC_COLUMNS or normalized in CAMERA_COLUMNS


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


@lru_cache(maxsize=1)
def fetch_alertas() -> list[dict[str, Any]]:
    settings = get_settings()
    with sql.connect(
        server_hostname=settings.databricks_server_hostname,
        http_path=settings.databricks_http_path,
        access_token=settings.databricks_token,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(QUERY)
            columns = [column[0].lower() for column in cursor.description]
            return [
                {
                    key: _json_value(value)
                    for key, value in zip(columns, row)
                    if _is_public_column(key)
                }
                for row in cursor.fetchall()
            ]


def clear_alertas_cache() -> None:
    fetch_alertas.cache_clear()
