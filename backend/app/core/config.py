from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/enercheck"

    # JWT
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # App
    APP_NAME: str = "EnerCheck API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    # "produccion" activa las validaciones de arranque (app/arranque.py) y oculta /api/docs
    ENTORNO: str = "desarrollo"

    @property
    def es_produccion(self) -> bool:
        return self.ENTORNO == "produccion"

    # Gemini Vision (OCR de boletas)
    GEMINI_API_KEY: str = ""

    # Landing: RUT del condominio cuyo sitio se muestra cuando el dominio de la petición no está
    # registrado en ningún condominio (localhost en desarrollo, hosts temporales). Vacío = 404.
    SITIO_POR_DEFECTO: str = ""

    # Super admin inicial de producción: app/arranque.py lo crea solo si no existe ninguno
    SUPERADMIN_EMAIL: str = ""
    SUPERADMIN_NOMBRE: str = "Super Admin"
    SUPERADMIN_PASSWORD: str = ""

    # Correo transaccional (invitaciones y recuperación de clave) vía Resend. Sin RESEND_API_KEY el
    # envío falla con un motivo claro y las invitaciones se reenvían por WhatsApp (spec acceso-por-enlace).
    RESEND_API_KEY: str = ""
    EMAIL_REMITENTE: str = ""          # p. ej. no-responder@comunidadsantalaura.cl (dominio verificado en Resend)
    # Portal al que apuntan los enlaces cuando el usuario no tiene condominio o este no tiene portal_url
    PORTAL_URL_POR_DEFECTO: str = "http://localhost:3000"


settings = Settings()
