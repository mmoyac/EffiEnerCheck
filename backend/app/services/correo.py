"""Correo transaccional por la API HTTP de Resend (spec acceso-por-enlace).

`enviar` nunca lanza: devuelve ResultadoEnvio(ok, motivo) para que el endpoint decida (p. ej. ofrecer
WhatsApp). Ni el cuerpo del correo ni el enlace se registran en los logs.
"""
import logging
from dataclasses import dataclass
from email.utils import formataddr
from html import escape

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

URL_RESEND = "https://api.resend.com/emails"
# Las pruebas reemplazan el transporte por uno falso (httpx.MockTransport).
transporte: httpx.AsyncBaseTransport | None = None


@dataclass
class ResultadoEnvio:
    ok: bool
    motivo: str | None = None


def configurado() -> bool:
    return bool(settings.RESEND_API_KEY and settings.EMAIL_REMITENTE)


async def enviar(destino: str, asunto: str, texto: str, html: str, nombre_remitente: str) -> ResultadoEnvio:
    if not configurado():
        return ResultadoEnvio(False, "El envío de correos no está configurado")
    remitente = formataddr((nombre_remitente.replace('"', "").strip() or "Comunidad", settings.EMAIL_REMITENTE))
    try:
        async with httpx.AsyncClient(timeout=10, transport=transporte) as cliente:
            r = await cliente.post(
                URL_RESEND,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": remitente, "to": [destino], "subject": asunto, "text": texto, "html": html},
            )
    except httpx.HTTPError as exc:
        log.warning("Resend no respondió: %s", type(exc).__name__)
        return ResultadoEnvio(False, "El servicio de correo no respondió")
    if r.status_code >= 300:
        log.warning("Resend rechazó el envío: HTTP %s", r.status_code)
        return ResultadoEnvio(False, f"El servicio de correo rechazó el envío (HTTP {r.status_code})")
    log.info("Correo enviado por Resend: %s", r.json().get("id") if r.content else "")
    return ResultadoEnvio(True)


# ---- Plantillas -----------------------------------------------------------------------------------------

def _html(parrafos: list[str], boton: str, url: str, pie: str) -> str:
    cuerpo = "".join(f'<p style="margin:0 0 16px">{p}</p>' for p in parrafos)
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;color:#1f2937;'
        'max-width:520px;margin:0 auto;padding:24px">'
        f"{cuerpo}"
        f'<p style="margin:24px 0"><a href="{escape(url, quote=True)}" style="background:#16a34a;color:#ffffff;'
        f'padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:bold">{boton}</a></p>'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6b7280">Si el botón no funciona, copia este enlace en '
        f'tu navegador:<br><span style="word-break:break-all">{escape(url)}</span></p>'
        f'<p style="margin:0;font-size:13px;color:#6b7280">{pie}</p>'
        "</div>"
    )


def invitacion(nombre: str, condominio: str, url: str) -> tuple[str, str, str]:
    """(asunto, texto, html) de la invitación a crear la clave."""
    n, c = escape(nombre), escape(condominio)
    asunto = f"Crea tu clave para el portal de {condominio}"
    texto = (
        f"Hola {nombre}:\n\n"
        f"Te invitamos al portal de {condominio}, donde podrás revisar tus cobros y participar en las "
        f"actividades de la comunidad.\n\n"
        f"Para entrar, crea tu clave en este enlace (vence en 7 días y sirve una sola vez):\n{url}\n\n"
        f"Tu usuario es este correo. Si no esperabas este mensaje, puedes ignorarlo.\n"
    )
    html = _html(
        [f"Hola {n}:",
         f"Te invitamos al portal de <strong>{c}</strong>, donde podrás revisar tus cobros y participar en "
         f"las actividades de la comunidad.",
         "Para entrar, crea tu clave. Tu usuario es este correo."],
        "Crear mi clave", url,
        "El enlace vence en 7 días y sirve una sola vez. Si no esperabas este mensaje, puedes ignorarlo.",
    )
    return asunto, texto, html


def recuperacion(nombre: str, condominio: str, url: str) -> tuple[str, str, str]:
    """(asunto, texto, html) del restablecimiento de clave."""
    n = escape(nombre)
    asunto = f"Restablece tu clave del portal de {condominio}"
    texto = (
        f"Hola {nombre}:\n\n"
        f"Recibimos una solicitud para restablecer tu clave del portal de {condominio}.\n\n"
        f"Crea una nueva en este enlace (vence en 1 hora y sirve una sola vez):\n{url}\n\n"
        f"Si no lo pediste, ignora este correo: tu clave actual sigue igual.\n"
    )
    html = _html(
        [f"Hola {n}:",
         f"Recibimos una solicitud para restablecer tu clave del portal de <strong>{escape(condominio)}</strong>."],
        "Crear una clave nueva", url,
        "El enlace vence en 1 hora y sirve una sola vez. Si no lo pediste, ignora este correo: tu clave actual "
        "sigue igual.",
    )
    return asunto, texto, html
