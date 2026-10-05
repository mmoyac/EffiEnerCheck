"""
Extrae datos de una boleta eléctrica usando Gemini Vision.
Devuelve un dict con los campos relevantes o lanza ValueError si falla.
"""
import json
import re

from google import genai
from google.genai import types

from app.core.config import settings

_MODEL = "gemini-2.5-flash"

_PROMPT = """
Analiza esta boleta o cuenta de electricidad chilena y extrae los siguientes campos en formato JSON.
Si un campo no aparece en la imagen devuelve null para ese campo.
Responde ÚNICAMENTE con el objeto JSON, sin texto adicional, sin markdown, sin bloques de código.

{
  "periodo_mes": "YYYY-MM-01",
  "total_kwh_compania": <número entero o null>,
  "monto_neto_electricidad_consumida": <número entero sin IVA o null>,
  "monto_total_emision": <monto total con IVA o null>,
  "monto_saldo_anterior": <saldo anterior o null>,
  "items_detalle": [
    {"descripcion": "<texto>", "monto_neto_clp": <entero con signo>, "tipo_calculo": "fijo|variable|informativo"}
  ]
}

Notas:
- periodo_mes es el primer día del mes de consumo en formato YYYY-MM-01
- Los montos son en pesos chilenos (CLP), enteros sin decimales ni puntos de miles
- monto_neto_electricidad_consumida es el Total neto SIN IVA (campo "Total neto" en la boleta)
- monto_total_emision es el campo "Total Emisión" CON IVA
- monto_saldo_anterior es el campo "Saldo anterior"
- En Chile el separador de miles es el punto: 4.547.354 = 4547354

QUÉ VA EN items_detalle:
- SOLO los cargos y abonos individuales del período que la compañía está cobrando.
- NO incluyas los totales ni subtotales: "Total exento", "Total neto", "19% IVA",
  "Total Emisión", "Otros", "Total a pagar". Esos ya se capturan en los campos de
  cabecera de este mismo JSON.
- NO incluyas el saldo anterior ni sus componentes: "Saldo Anterior", "Saldo Anterior
  Servicio Eléctrico", "Otro Saldo Anterior", "Saldo Anterior Vencido". Corresponden a
  deuda de períodos previos, no a cargos de este período, y van en monto_saldo_anterior.

SIGNO DE LOS ÍTEMS (importante):
- Los cargos normales van con monto POSITIVO.
- Todo concepto que RESTA del total va con monto NEGATIVO. Incluye descuentos,
  rebajas, notas de crédito, abonos, devoluciones, bonificaciones, reintegros,
  compensaciones y reliquidaciones a favor del cliente.
- Devuelve el signo negativo aunque en la boleta el número aparezca sin signo,
  entre paréntesis, o con la palabra "menos", "descuento" o "abono" al lado.
  Ejemplo: una línea "DESCUENTO LEY 20.928  50.000" se devuelve como -50000.
- No inviertas el signo de un cargo normal solo porque su descripción sea larga
  o poco clara: en la duda, un concepto que la compañía cobra es positivo.
"""


def _clean_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


async def extraer_datos_boleta(image_bytes: bytes, mime_type: str) -> dict:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada en el servidor")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[
                types.Part.from_text(text=_PROMPT),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise ValueError(
                "Cuota de Gemini agotada. Verifica tu plan en https://ai.dev/rate-limit o habilita facturación en Google AI Studio."
            ) from exc
        raise ValueError(f"Error al llamar a Gemini: {msg[:200]}") from exc

    raw = _clean_response(response.text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini no devolvió JSON válido: {raw[:300]}") from exc

    return data
