# Importa Base y todos los modelos para que Alembic los detecte en autogenerate.
# Este módulo NO debe usarse en el código de la aplicación; es solo para migraciones.
from app.models.base import Base  # noqa: F401
from app.models.usuario_parcela import usuario_parcelas  # noqa: F401
from app.models.menu import Menu, menu_roles  # noqa: F401
from app.models.auditoria import AuditoriaLog  # noqa: F401
from app.models.boleta import BoletaItemDetalle, BoletaMaestra  # noqa: F401
from app.models.condominio import Condominio  # noqa: F401
from app.models.enlace_acceso import EnlaceAcceso  # noqa: F401
from app.models.lectura import LecturaParcela  # noqa: F401
from app.models.liquidacion import LiquidacionParcela  # noqa: F401
from app.models.parcela import Parcela  # noqa: F401
from app.models.rifa import CompraRifa, ImputacionRifa, Rifa, RifaNumero  # noqa: F401
from app.models.rol import Rol  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
