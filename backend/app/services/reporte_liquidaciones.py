"""
PDF con las liquidaciones de un período: datos de la boleta, desglose de cargos, una fila por parcela y el
cuadre de la suma contra el total de emisión. Es el respaldo que la administración guarda o comparte.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fpdf import FPDF

from app.utils.format import periodo_label

_TIPOS = {"fijo": "Fijo", "variable": "Variable", "informativo": "Informativo", "pendiente": "Sin clasificar"}


def _clp(monto: float) -> str:
    texto = f"{round(monto):,}".replace(",", ".")
    return f"-${texto[1:]}" if texto.startswith("-") else f"${texto}"


def _num(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".") if valor == int(valor) else f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Las fuentes base del PDF solo cubren Latin-1: los textos vienen de la administración o del OCR y pueden traer
# signos tipográficos. Se traducen a su equivalente simple y lo demás se reemplaza por "?", sin que el PDF falle.
_EQUIVALENTES = str.maketrans({"−": "-", "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
                               "…": "...", "•": "·", " ": " "})


def _latin1(texto: str) -> str:
    return texto.translate(_EQUIVALENTES).encode("latin-1", "replace").decode("latin-1")


class _Pdf(FPDF):
    def normalize_text(self, text):
        return super().normalize_text(_latin1(text))

    def __init__(self, titulo: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titulo = titulo
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(12, 12, 12)

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", size=7)
        self.set_text_color(120)
        self.cell(0, 4, f"{self.titulo} · página {self.page_no()}/{{nb}}", align="C")


def generar_pdf(condominio: str, boleta, filas: list[dict]) -> bytes:
    """
    `filas`: una por parcela, en orden natural, con numero_parcela, lectura_anterior, lectura_actual, kwh,
    energia, variable, fija y total.
    """
    periodo = periodo_label(boleta.periodo_mes)
    pdf = _Pdf(f"Liquidaciones {periodo} · {condominio}")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Encabezado
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, f"Liquidaciones de luz · {periodo}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(90)
    generado = datetime.now(ZoneInfo("America/Santiago")).strftime("%d-%m-%Y %H:%M")
    pdf.cell(0, 5, f"{condominio} · generado el {generado}", new_x="LMARGIN", new_y="NEXT")
    if boleta.boleta_visible_usuarios:
        estado, color = "Período publicado", (22, 128, 61)
    elif boleta.liquidaciones_cerradas:
        estado, color = "Período cerrado, aún sin publicar", (161, 98, 7)
    else:
        estado, color = "BORRADOR: el período no está cerrado y los montos pueden cambiar", (185, 28, 28)
    pdf.set_text_color(*color)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, estado, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(2)

    # Datos de la boleta
    kwh_compania = boleta.total_kwh_compania or 0
    kwh_parcelas = sum(f["kwh"] for f in filas)
    items = [i for i in boleta.items_detalle]
    suma_fijo = sum(i.monto_neto_clp for i in items if i.tipo_calculo == "fijo")
    suma_variable = sum(i.monto_neto_clp for i in items if i.tipo_calculo == "variable")
    emision = boleta.monto_total_emision or 0
    valor_kwh = (emision - suma_fijo - suma_variable) / kwh_compania if kwh_compania else 0

    def dato(etiqueta: str, valor: str):
        pdf.set_font("Helvetica", size=9)
        pdf.cell(60, 5, etiqueta)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, valor, new_x="LMARGIN", new_y="NEXT")

    dato("Total emisión de la boleta", _clp(emision))
    dato("kWh de la compañía", f"{_num(kwh_compania)} kWh")
    dato("kWh registrados por las parcelas", f"{_num(kwh_parcelas)} kWh")
    dato("Diferencial (no registrado)", f"{_num(kwh_compania - kwh_parcelas)} kWh · {_clp((kwh_compania - kwh_parcelas) * valor_kwh)}")
    dato("Valor del kWh", f"${valor_kwh:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    pdf.ln(2)

    # Desglose de cargos
    if items:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Cargos de la boleta (con IVA)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        orden = {"fijo": 0, "variable": 1, "informativo": 2, "pendiente": 3}
        for item in sorted(items, key=lambda i: orden.get(i.tipo_calculo, 9)):
            pdf.cell(110, 4.5, item.descripcion[:70])
            pdf.cell(30, 4.5, _TIPOS.get(item.tipo_calculo, item.tipo_calculo))
            pdf.cell(0, 4.5, _clp(item.monto_neto_clp), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(90)
        pdf.multi_cell(0, 4, "Fijo: partes iguales entre las parcelas. Variable y diferencial: según el consumo de cada "
                             "parcela. Energía: kWh de la parcela por el valor del kWh.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.ln(2)

    # Tabla por parcela
    columnas = [("Parcela", 22, "L"), ("Lect. anterior", 24, "R"), ("Lect. actual", 24, "R"), ("kWh", 16, "R"),
                ("Energía", 24, "R"), ("Variable", 24, "R"), ("Fijo", 20, "R"), ("Total", 32, "R")]

    def encabezado():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(230, 233, 238)
        for titulo, ancho, alin in columnas:
            pdf.cell(ancho, 6, titulo, border="B", align=alin, fill=True)
        pdf.ln()

    encabezado()
    pdf.set_font("Helvetica", size=8)
    for n, f in enumerate(filas):
        if pdf.will_page_break(5):
            pdf.add_page()
            encabezado()
            pdf.set_font("Helvetica", size=8)
        pdf.set_fill_color(246, 247, 249)
        valores = [f["numero_parcela"], _num(f["lectura_anterior"]), _num(f["lectura_actual"]), _num(f["kwh"]),
                   _clp(f["energia"]), _clp(f["variable"]), _clp(f["fija"]), _clp(f["total"])]
        for (_, ancho, alin), valor in zip(columnas, valores):
            pdf.cell(ancho, 5, valor, align=alin, fill=n % 2 == 1)
        pdf.ln()

    # Totales y cuadre
    total = sum(f["total"] for f in filas)
    pdf.set_font("Helvetica", "B", 8)
    totales = ["TOTAL", "", "", _num(kwh_parcelas), _clp(sum(f["energia"] for f in filas)),
               _clp(sum(f["variable"] for f in filas)), _clp(sum(f["fija"] for f in filas)), _clp(total)]
    for (_, ancho, alin), valor in zip(columnas, totales):
        pdf.cell(ancho, 6, valor, border="T", align=alin)
    pdf.ln(9)

    pdf.set_font("Helvetica", "B", 10)
    if total == emision:
        pdf.set_text_color(22, 128, 61)
        pdf.cell(0, 6, f"Cuadre: la suma de las liquidaciones ({_clp(total)}) es igual al total emisión ({_clp(emision)}).")
    else:
        pdf.set_text_color(185, 28, 28)
        pdf.cell(0, 6, f"Atención: la suma de las liquidaciones ({_clp(total)}) difiere del total emisión "
                       f"({_clp(emision)}) en {_clp(total - emision)}.")
    pdf.set_text_color(0)
    return bytes(pdf.output())
