from pydantic import BaseModel, ConfigDict


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    path: str
    icon: str | None
    orden: int
    parent_id: int | None
    modulo: str | None = None  # None = núcleo del portal
