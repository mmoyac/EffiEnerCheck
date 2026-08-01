from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditoriaLogResponse(BaseModel):
    """Solo lectura: los logs los genera el middleware de auditoría."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    condominio_id: int | None
    usuario_id: int
    accion: str
    detalles: Any | None   # {"before": {...}, "after": {...}}
    ip_address: str | None
    created_at: datetime
