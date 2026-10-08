from pydantic import BaseModel, ConfigDict


class ParcelaCreate(BaseModel):
    condominio_id: int
    numero_parcela: str
    propietario_nombre: str | None = None
    activa: bool = True


class ParcelaUpdate(BaseModel):
    numero_parcela: str | None = None
    propietario_nombre: str | None = None
    activa: bool | None = None


class ParcelaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    condominio_id: int
    numero_parcela: str
    propietario_nombre: str | None
    activa: bool
    orden_recorrido: int | None = None


class OrdenRecorridoUpdate(BaseModel):
    """Recorrido del lector: parcelas en el orden en que se caminan. Lista vacía = sin recorrido."""
    condominio_id: int | None = None   # super_admin
    parcela_ids: list[int]
