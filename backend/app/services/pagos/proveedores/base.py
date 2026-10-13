"""
Contrato de un proveedor de pagos. Un proveedor nuevo = una subclase de `Adaptador` registrada en
`proveedores/__init__.py`; el flujo, las pantallas y la contabilidad no cambian.

Regla: lo que llega por el navegador o por la notificación solo IDENTIFICA la transacción; el
resultado lo dan `verificar` y `consultar`, que preguntan al proveedor de servidor a servidor.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

EstadoResultado = Literal["APROBADO", "RECHAZADO", "PENDIENTE"]


class ErrorProveedor(RuntimeError):
    """El proveedor no respondió o respondió algo inesperado (red, 5xx, formato)."""


class ErrorCredenciales(ErrorProveedor):
    """El proveedor rechazó las credenciales de la pasarela."""


@dataclass(frozen=True)
class CampoCredencial:
    nombre: str
    etiqueta: str
    secreto: bool = True


@dataclass(frozen=True)
class Urls:
    retorno: str
    cancelacion: str
    notificacion: str

    @property
    def notificacion_publica(self) -> bool:
        """Solo una URL https es alcanzable desde internet (en desarrollo, con URL_PUBLICA_PAGOS)."""
        return self.notificacion.startswith("https://")


@dataclass(frozen=True)
class Redireccion:
    url: str
    metodo: Literal["GET", "POST"] = "GET"
    campos: dict[str, str] = field(default_factory=dict)
    token: str | None = None
    transaccion: str | None = None


@dataclass(frozen=True)
class Resultado:
    estado: EstadoResultado
    monto: int | None = None
    transaccion: str | None = None
    orden_comercio: str | None = None
    autorizacion: str | None = None
    ultimos_digitos: str | None = None
    medio: str | None = None
    motivo: str | None = None
    # Solo claves de la lista blanca del adaptador: nunca datos personales del pagador
    datos: dict[str, Any] = field(default_factory=dict)


@dataclass
class PasarelaEnUso:
    """Lo que el adaptador necesita de una pasarela: sus credenciales ya descifradas, en memoria."""
    id: int
    ambiente: str
    credenciales: dict[str, str]


@dataclass
class IntencionEnUso:
    id: str
    orden_comercio: str
    total: int
    descripcion: str
    email: str | None
    segundos_restantes: int
    token: str | None = None
    transaccion: str | None = None


class Adaptador(ABC):
    proveedor: str
    nombre: str
    campos_credenciales: list[CampoCredencial]
    requiere_email: bool = False
    monto_minimo: int = 1
    # El retorno no trae datos del proveedor: la intención va en la URL (?intencion=<id>)
    retorno_por_intencion: bool = False

    def __init__(self, http: httpx.AsyncClient | None = None):
        # Inyectable: los tests pasan un httpx.AsyncClient con MockTransport
        self._http = http

    def cliente(self) -> httpx.AsyncClient:
        return self._http or httpx.AsyncClient(timeout=20)

    async def _enviar(self, request: httpx.Request) -> httpx.Response:
        cliente = self.cliente()
        try:
            return await cliente.send(request)
        except httpx.HTTPError as exc:
            raise ErrorProveedor(f"Sin respuesta del proveedor: {type(exc).__name__}") from exc
        finally:
            if self._http is None:
                await cliente.aclose()

    @abstractmethod
    async def crear(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso, urls: Urls) -> Redireccion: ...

    @abstractmethod
    def token_de(self, datos: dict[str, Any]) -> str | None:
        """Identificador de la transacción en el retorno o la notificación (solo identifica)."""

    @abstractmethod
    async def verificar(self, pasarela: PasarelaEnUso, token: str) -> Resultado: ...

    @abstractmethod
    async def consultar(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso) -> Resultado: ...

    @abstractmethod
    async def probar(self, pasarela: PasarelaEnUso) -> None:
        """Prueba de conexión sin crear cobros. Lanza ErrorCredenciales o ErrorProveedor."""

    async def anular(self, pasarela: PasarelaEnUso, token: str) -> bool:
        """Elimina en el proveedor una transacción cancelada. True solo si el proveedor lo confirmó."""
        return False


def filtrar(datos: dict[str, Any], permitidas: set[str]) -> dict[str, Any]:
    return {k: v for k, v in datos.items() if k in permitidas}
