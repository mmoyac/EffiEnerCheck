# Rifas solidarias

Módulo para organizar colectas con rifa dentro del condominio, por ejemplo para ayudar a un vecino. Los números se venden **en la portería** o los compran los vecinos **desde el portal**. Lo recaudado se paga en efectivo, por transferencia a la cuenta de la comunidad o se **imputa al gasto común**, que se cobra en Comunidad Feliz. La rifa no toca la boleta eléctrica, las liquidaciones ni el Motor EnerCheck.

Spec: [`openspec/changes/rifas-solidarias/specs/rifas-solidarias/spec.md`](../openspec/changes/rifas-solidarias/specs/rifas-solidarias/spec.md) (pasa a `openspec/specs/rifas-solidarias/` al archivar el cambio).

## Flujo

```
Admin crea la rifa (premios, precio, cantidad de números, datos para transferir)  → abierta
→ Portería vende: parcela → números → comprador → forma de pago → (voucher) → teléfono
     ↳ comprobante: WhatsApp con el mensaje listo, o folio en pantalla / impreso
→ Vecinos compran desde /mis-rifas (transferencia o gasto común)
→ Admin confirma las transferencias revisando el voucher
→ Admin cierra la rifa → cerrada + una imputación al gasto común por parcela
→ Admin descarga el CSV, lo carga en Comunidad Feliz y marca cada imputación como cargada
→ Admin descarga la lista para el sorteo (el sorteo es fuera del sistema)
```

## Formas de pago

| Forma | Quién puede usarla | Estado |
|-------|--------------------|--------|
| Efectivo | Portería y administración | Pagada al registrar. Suma en la **caja** del día. |
| Transferencia | Todos | Pendiente hasta que el admin la confirma. En portería exige **foto del voucher**; en el portal el voucher es opcional y se puede adjuntar después. |
| Gasto común | Todos | Al cerrar la rifa genera una **imputación** por parcela para cargar en Comunidad Feliz. |

## Reglas

| Regla | Detalle |
|-------|---------|
| A nombre de quién | Toda compra queda a nombre de una parcela. En portería el comprador es texto libre (puede ser alguien de fuera); por defecto se propone el propietario. |
| Número único | `UNIQUE (rifa_id, numero)` + bloqueo de la rifa. Dos ventas simultáneas del mismo número: una gana y la otra recibe `409`. |
| Folio | `R<rifa>-<correlativo>` (p. ej. `R3-042`). Se muestra en grande tras la venta para anotarlo si el comprador no tiene teléfono. Sirve para buscar la compra en portería. |
| Teléfono | Se proponen los teléfonos de los residentes de la parcela (editables). Se normalizan a `56XXXXXXXXX`. |
| Comprobante | Enlace `wa.me` con el mensaje listo: la portería toca «Enviar» en WhatsApp. El sistema no envía mensajes. Botón «Imprimir» opcional (formato de impresora térmica). |
| Anular | Solo con la rifa abierta. El admin anula cualquiera; el vecino, lo que compró él desde el portal si no está pagado. **La portería no anula.** |
| Privacidad | La grilla del vecino muestra qué números están tomados, no de quién. Los vouchers se guardan fuera del estático público y solo los ven el staff y los usuarios de esa parcela. |
| Editar | Nombre, beneficiario, descripción, premios y datos para transferir, mientras esté abierta. El precio se bloquea con el primer número vendido. La cantidad puede crecer, pero no bajar del mayor número vendido. |
| Reabrir | Solo si ninguna imputación está marcada como cargada. Borra las imputaciones. |

## Endpoints (`/api/v1/rifas`)

| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/rifas/?estado=abierta` | Todos |
| POST / PATCH | `/rifas/`, `/rifas/{id}` | Admin |
| GET | `/rifas/{id}` | Todos (respuesta recortada según la parcela) |
| POST | `/rifas/{id}/compras` | Todos — multipart: `datos` (JSON) + `voucher` |
| GET | `/rifas/{id}/compras?parcela_id=&folio=` | Admin, portería |
| POST | `/rifas/{id}/compras/{cid}/anular` | Admin, o el autor desde el portal |
| POST | `/rifas/{id}/compras/{cid}/confirmar-pago` | Admin (solo transferencias) |
| POST / GET | `/rifas/{id}/compras/{cid}/voucher` | Adjuntar: autor o staff · Ver: staff o usuarios de la parcela |
| GET | `/rifas/{id}/parcelas`, `/rifas/{id}/telefonos?parcela_id=` | Admin, portería |
| GET | `/rifas/{id}/caja` | Admin, portería |
| POST | `/rifas/{id}/cerrar`, `/rifas/{id}/reabrir` | Admin |
| PATCH | `/rifas/{id}/imputaciones/{iid}` | Admin — `{cargada}` |
| GET | `/rifas/{id}/imputaciones.csv` | Admin — para Comunidad Feliz |
| GET | `/rifas/{id}/export.csv` | Admin — lista para el sorteo |
| GET | `/rifas/{id}/eliminacion` | **Solo super admin**: resumen de lo que se borrará |
| DELETE | `/rifas/{id}?confirmacion=<nombre>` | **Solo super admin**: borra la rifa con sus compras, números, imputaciones y vouchers |

Los CSV salen en UTF-8 con BOM, separados por `;` y con hora de Chile.

Auditoría: `CREATE_RIFA`, `UPDATE_RIFA`, `COMPRAR_RIFA`, `ANULAR_COMPRA_RIFA`, `CONFIRMAR_PAGO_RIFA`, `CERRAR_RIFA`, `REABRIR_RIFA`, `MARCAR_IMPUTACION_RIFA`, `ELIMINAR_RIFA` (con el resumen de lo borrado).

**Eliminar una rifa** (botón "Eliminar rifa" en el detalle, solo super admin): sirve en cualquier estado y es irreversible. Muestra antes qué se borrará y exige escribir el nombre exacto. Si hay imputaciones ya cargadas en Comunidad Feliz, lo advierte: esos cobros hay que revertirlos allá a mano. Si fue un error, la única vuelta atrás son los respaldos (DEPLOY.md §7).

## Pantallas

| Ruta | Quién | Archivo |
|------|-------|---------|
| `/porteria` | Portería (`porteria@santalaura.cl`) | `pages/porteria/VentaRifa.tsx`: Vender, Buscar compra, Caja |
| `/rifas`, `/rifas/:id` | Admin (sidebar «Rifas») | `pages/admin/Rifas.tsx`, `RifaDetalle.tsx`: Compras, Registrar venta, Gasto común, Caja |
| `/mis-rifas`, `/mis-rifas/:id` | Parcelero (aviso en `/liquidaciones` y enlace en la cabecera) | `pages/parcelero/Rifas.tsx` |

Componentes compartidos en `components/rifas/`: `NumeroGrid` (sobre 200 números pagina en rangos de 100), `CompraPanel`, `ParcelaBuscador`, `VoucherInput` (reduce las fotos a 1600 px JPEG antes de subirlas), `ComprobanteVenta`, `ComprasLista` y `CajaResumen`.

## Despliegue

Los vouchers viven en el volumen `privado_data` (`/app/privado`). Respáldalo junto con `postgres_data` y `uploads_data`.
