"""
Archivos de las fotos del medidor (cambio foto-medidor).

Viven en /app/privado/lecturas (volumen privado, respaldado), NUNCA en /app/uploads, que se sirve como
estático público. Solo se entregan por GET /lecturas/{id}/foto con control de acceso.
"""
import hashlib
import os
import uuid

FOTOS_DIR = "/app/privado/lecturas"
FOTO_MAX_BYTES = 3 * 1024 * 1024


def tipo_por_bytes(contenido: bytes) -> str | None:
    """Extensión según la firma del archivo (no se confía en el content-type del cliente)."""
    if contenido[:3] == b"\xff\xd8\xff":
        return "jpg"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    return None


def sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def guardar(contenido: bytes, extension: str) -> str:
    os.makedirs(FOTOS_DIR, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(FOTOS_DIR, nombre), "wb") as f:
        f.write(contenido)
    return nombre


def ruta(nombre: str) -> str:
    return os.path.join(FOTOS_DIR, nombre)


def borrar(nombre: str | None) -> None:
    if nombre:
        try:
            os.remove(ruta(nombre))
        except FileNotFoundError:
            pass
