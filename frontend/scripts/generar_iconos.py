"""Íconos de la app (PWA) desde el diseño del favicon. Uso: python frontend/scripts/generar_iconos.py (requiere Pillow)."""
import math
import os

from PIL import Image, ImageDraw

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "icons")
VERDE = (22, 163, 74, 255)
BLANCO = (255, 255, 255, 255)
GRANDE = 2048   # se dibuja grande y se reduce: bordes suaves


def cubica(p0, p1, p2, p3, n=40):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d
                  for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i / n for i in range(n + 1))]


def arco(cx, cy, r, desde, hasta, n=60):
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in (desde + (hasta - desde) * i / n for i in range(n + 1))]


def trazos():
    """Trazos del ícono en unidades de 24x24 (viewBox de lucide)."""
    cuerpo = arco(10, 21, 8, 180, 360)                     # M18 21a8 8 0 0 0-16 0
    cabeza = arco(10, 8, 5, 0, 360, 90)                    # circle cx=10 cy=8 r=5
    # M22 20 c0-3.37-2-6.5-4-8 a5 5 0 0 0-.45-8.3
    lado = cubica((22, 20), (22, 16.63), (20, 13.5), (18, 12))
    # arco de (18,12) a (17.55,3.7), radio 5, recorrido por la derecha (centro ~ (13.9, 7.9))
    cx, cy = 13.78, 7.86
    a0 = math.degrees(math.atan2(12 - cy, 18 - cx))
    a1 = math.degrees(math.atan2(3.7 - cy, 17.55 - cx))
    lado += arco(cx, cy, math.hypot(18 - cx, 12 - cy), a0, a1 if a1 < a0 else a1 - 360)
    return [cuerpo, cabeza, lado]


def dibujar(tam, *, radio_fondo, escala_glifo):
    img = Image.new("RGBA", (GRANDE, GRANDE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if radio_fondo:
        d.rounded_rectangle([0, 0, GRANDE - 1, GRANDE - 1], radius=int(GRANDE * radio_fondo), fill=VERDE)
    else:
        d.rectangle([0, 0, GRANDE, GRANDE], fill=VERDE)
    lado = GRANDE * escala_glifo           # el glifo (24 u) ocupa esta fracción del ícono
    u = lado / 24
    ox = oy = (GRANDE - lado) / 2
    grosor = max(2, int(2 * u))
    for trazo in trazos():
        pts = [(ox + x * u, oy + y * u) for x, y in trazo]
        # Trazo redondeado: círculos estampados a lo largo de la curva (sin uniones dentadas)
        r = grosor / 2
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            pasos = max(1, int(math.hypot(x1 - x0, y1 - y0) / (r / 4)))
            for i in range(pasos + 1):
                x, y = x0 + (x1 - x0) * i / pasos, y0 + (y1 - y0) * i / pasos
                d.ellipse([x - r, y - r, x + r, y + r], fill=BLANCO)
    return img.resize((tam, tam), Image.LANCZOS)


os.makedirs(SALIDA, exist_ok=True)
dibujar(192, radio_fondo=0.22, escala_glifo=0.62).save(os.path.join(SALIDA, "icon-192.png"))
dibujar(512, radio_fondo=0.22, escala_glifo=0.62).save(os.path.join(SALIDA, "icon-512.png"))
# Maskable: fondo a sangre (Android recorta la forma) y glifo dentro de la zona segura (círculo del 80%)
dibujar(512, radio_fondo=0, escala_glifo=0.50).save(os.path.join(SALIDA, "icon-maskable-512.png"))
# iPhone redondea las esquinas solo: fondo cuadrado, sin transparencia
dibujar(180, radio_fondo=0, escala_glifo=0.60).convert("RGB").save(os.path.join(SALIDA, "apple-touch-icon.png"))
print(sorted(os.listdir(SALIDA)))
