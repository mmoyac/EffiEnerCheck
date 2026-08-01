import datetime

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def periodo_label(periodo_mes) -> str:
    """2025-03-01 → 'Mar. 2025'"""
    if isinstance(periodo_mes, str):
        periodo_mes = datetime.date.fromisoformat(periodo_mes)
    if isinstance(periodo_mes, datetime.datetime):
        periodo_mes = periodo_mes.date()
    return f"{_MESES[periodo_mes.month - 1]}. {periodo_mes.year}"
