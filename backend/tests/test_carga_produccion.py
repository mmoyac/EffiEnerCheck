"""Carga de producción: planilla de residentes y bloqueo de la clave pública del seed."""
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.arranque import usuarios_con_clave_conocida
from app.db.cargar_residentes import cargar, leer_planilla
from app.models.parcela import Parcela
from app.models.usuario import Usuario


def _planilla(ruta):
    """Misma forma que MATRIZ RESIDENTES.xlsx: títulos arriba, columna vacía a la izquierda. Datos ficticios."""
    wb = Workbook()
    ws = wb.active
    ws.append([])
    ws.append(["", "Residentes"])
    ws.append(["", "Condominio Prueba"])
    ws.append([])
    ws.append(["", "Unidad", "Prorrateo", "Nombre y apellido", "Rol", "Estado de rol", "Encargado",
               "Correo", "Teléfono", "RUT"])
    ws.append(["", 2, 0.02, "Ana  Pérez ", "Arrendatario", None, "Sí", "ana@ejemplo.cl", "9 1234 5678", None])
    ws.append(["", 2, 0.02, "Beto Soto", "Dueño", "Sin validar", "Sí", "Beto@Ejemplo.cl", 56911112222, None])
    ws.append(["", "13 A", 0.01, "Carla Rojas", "Dueño", "Sin validar", "No", "carla@ejemplo.cl", "123", None])
    ws.append(["", 10, 0.02, "Dani Vera", "Familiar", None, "No", "dani@ejemplo.cl", None, None])
    wb.save(ruta)


async def test_carga_de_residentes_es_idempotente(db, tmp_path):
    ruta = tmp_path / "residentes.xlsx"
    _planilla(ruta)
    residentes, avisos = leer_planilla(ruta)

    assert [r.unidad for r in residentes] == ["2", "2", "13 A", "10"]
    assert residentes[0].nombre == "Ana Pérez"
    assert residentes[0].telefono == "56912345678"
    assert residentes[1].email == "beto@ejemplo.cl"
    assert any("teléfono inválido" in a for a in avisos)

    kwargs = dict(condominio_nombre="Condominio Prueba", rut="88888888-8", clave_hash="hash-de-prueba")
    primera = await cargar(db, residentes, **kwargs)
    assert (primera.condominio_creado, primera.parcelas_creadas, primera.usuarios_creados,
            primera.asignaciones_creadas) == (True, 3, 4, 4)

    segunda = await cargar(db, residentes, **kwargs)
    assert (segunda.condominio_creado, segunda.parcelas_creadas, segunda.usuarios_creados,
            segunda.asignaciones_creadas) == (False, 0, 0, 0)

    # El propietario de la parcela es el Dueño, aunque el Arrendatario aparezca antes en la planilla
    parcela_2 = (await db.execute(
        select(Parcela).where(Parcela.numero_parcela == "2", Parcela.propietario_nombre == "Beto Soto")
    )).scalar_one()
    beto = (await db.execute(
        select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas))
        .where(Usuario.email == "beto@ejemplo.cl")
    )).scalar_one()
    assert beto.rol.nombre == "parcelero"
    assert [p.id for p in beto.parcelas] == [parcela_2.id]


async def test_detecta_cuentas_con_la_clave_del_seed(db):
    # La base de CI tiene los usuarios del seed de desarrollo, todos con la clave pública.
    expuestos = await usuarios_con_clave_conocida(db)
    assert "hhernandez@santalaura.cl" in expuestos
