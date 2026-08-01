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
