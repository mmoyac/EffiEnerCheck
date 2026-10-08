from app.schemas.auth import LoginRequest, TokenPayload, TokenResponse
from app.schemas.auditoria import AuditoriaLogResponse
from app.schemas.boleta import (
    BoletaItemDetalleCreate,
    BoletaItemDetalleResponse,
    BoletaMaestraCreate,
    BoletaMaestraComuneroResponse,
    BoletaMaestraResponse,
    BoletaMaestraUpdate,
)
from app.schemas.condominio import CondominioCreate, CondominioResponse, CondominioUpdate
from app.schemas.lectura import LecturaParcelaCreate, LecturaParcelaResponse, LecturaParcelaUpdate
from app.schemas.liquidacion import LiquidacionParcelaResponse, MarcarPagadoRequest
from app.schemas.parcela import ParcelaCreate, ParcelaResponse, ParcelaUpdate
from app.schemas.rol import RolResponse
from app.schemas.usuario import UsuarioCreate, UsuarioDetailResponse, UsuarioResponse, UsuarioUpdate

__all__ = [
    "LoginRequest", "TokenPayload", "TokenResponse",
    "AuditoriaLogResponse",
    "BoletaItemDetalleCreate", "BoletaItemDetalleResponse",
    "BoletaMaestraCreate", "BoletaMaestraUpdate", "BoletaMaestraResponse", "BoletaMaestraComuneroResponse",
    "CondominioCreate", "CondominioUpdate", "CondominioResponse",
    "LecturaParcelaCreate", "LecturaParcelaUpdate", "LecturaParcelaResponse",
    "LiquidacionParcelaResponse", "MarcarPagadoRequest",
    "ParcelaCreate", "ParcelaUpdate", "ParcelaResponse",
    "RolResponse",
    "UsuarioCreate", "UsuarioUpdate", "UsuarioResponse", "UsuarioDetailResponse",
]
