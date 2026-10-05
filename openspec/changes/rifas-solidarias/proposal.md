# Proposal

## Why

En los condominios aparecen colectas solidarias, como una rifa para ayudar a un vecino, que hoy se organizan con papel, WhatsApp y planillas. Nadie sabe con certeza quién compró qué número y cobrar después es engorroso. EnerCheck ya identifica a cada usuario con su parcela y tiene la confianza de la comunidad como fuente de cobros, así que puede registrar la venta y dejar el cobro trazable. Para eso la rifa debe quedar **separada de la boleta eléctrica**, que tiene que seguir cuadrando exactamente con la emisión de la compañía.

La primera rifa real (Santa Laura) definió cómo se vende en la práctica: **la portería vende los números** a cualquier persona, cada venta queda a nombre de una parcela, el comprador paga en efectivo, por transferencia a la cuenta de la comunidad o pidiendo que se impute en el gasto común, y recibe sus números por mensaje. El gasto común se cobra en **Comunidad Feliz**, no en EnerCheck: desde aquí solo se informa qué imputar a cada parcela. Muchos comuneros son mayores, así que comprar en la portería, sin usar el teléfono, debe ser tan válido como comprar desde la app.

## What Changes

- Nuevo módulo **Rifas solidarias**, por condominio. El administrador crea una rifa con nombre, beneficiario, descripción, **lista de premios**, **datos para transferir**, precio por número y cantidad de números (del 1 al N).
- **Nuevo rol `porteria`**: una cuenta compartida por los turnos, que solo puede vender números de rifas abiertas de su condominio y ver su caja. No accede a boletas, lecturas, liquidaciones ni usuarios.
- **Venta en portería**: se elige la parcela; el sistema propone los teléfonos registrados de sus residentes (editable); se eligen los números en la grilla; se indica el nombre del comprador (opcional: puede ser cualquier persona) y la forma de pago.
- **Forma de pago por compra**: `efectivo` (queda pagada en el acto; solo portería o administración), `transferencia` (pendiente hasta que el administrador la confirma) o `gasto_comun` (se imputa a la parcela en Comunidad Feliz).
- **Comprobante por WhatsApp**: al confirmar la venta, la app abre WhatsApp con el teléfono y un mensaje listo (rifa, números, monto, forma de pago, premios). No se envía nada automáticamente.
- **Compra desde el portal del parcelero**: grilla, se tocan los números y se confirma, con pago por `transferencia` o `gasto_comun`. Sin límite de números por parcela.
- **Visibilidad y anulación**: los usuarios de una parcela ven sus compras. Mientras la rifa esté abierta, el parcelero puede anular sus propias compras no pagadas y el administrador cualquiera. La portería no anula.
- **Cierre**: las compras quedan firmes y se genera la **lista de imputaciones al gasto común** por parcela (solo las compras `gasto_comun`), exportable en CSV para cargarla en Comunidad Feliz. El administrador marca cada imputación como cargada. Se puede reabrir mientras ninguna esté marcada.
- **Caja de portería**: resumen del efectivo recibido por día, para cuadrar al retirar el dinero.
- **Lista para el sorteo**: CSV con números, parcela, comprador y forma de pago. El sorteo se hace fuera del sistema.
- **Teléfono de contacto** en la cuenta de usuario, cargado desde la planilla de residentes.
- **No se toca** la boleta maestra, las liquidaciones ni el Motor EnerCheck.

Fuera de alcance: el sorteo y el registro de ganadores, el pago en línea, el envío automático de mensajes (API de WhatsApp Business o SMS), la integración automática con Comunidad Feliz y el acceso sin contraseña (se propondrá aparte).

## Capabilities

### New Capabilities

- `rifas-solidarias`: ciclo de vida de una rifa con sus premios, venta en portería y compra desde el portal, formas de pago, comprobante por WhatsApp, anulación, imputaciones al gasto común, caja de portería, exportaciones, aislamiento multitenant y acciones de auditoría propias.

### Modified Capabilities

- `control-acceso-multitenant`: se agrega el rol `porteria` con su guarda propia, que queda **fuera** de `AnyRoleRequired`, y su pantalla de inicio.
- `gestion-usuarios`: las cuentas tienen un teléfono de contacto opcional.

Las acciones de auditoría del módulo se declaran en la spec nueva, sin modificar `auditoria`, que ya modifica el cambio en curso `items-credito-y-validacion` (ver design.md).

## Impact

**Backend**
- Modelos nuevos: `Rifa`, `CompraRifa`, `RifaNumero` y `CobroRifa` (imputaciones). Campo nuevo `Usuario.telefono`. Rol nuevo `porteria`. Migraciones Alembic.
- `app/core/dependencies.py`: guardas `PorteriaRequired` y `RifaAccesoRequired`; `AnyRoleRequired` mantiene los cuatro roles originales.
- Schemas en `app/schemas/rifa.py`; `telefono` en los schemas de usuario.
- Endpoints en `app/api/v1/endpoints/rifas.py` (prefijo `/rifas`).
- Seeds: rol `porteria`, usuario de portería y menú "Rifas".

**Frontend**
- Cliente `src/api/rifas.ts` y tipos.
- Administración: `pages/admin/Rifas.tsx`, `RifaDetalle.tsx`, `RifaFormModal.tsx` (premios, datos de transferencia, imputaciones, caja).
- Parcelero: `pages/parcelero/Rifas.tsx` y el aviso en `MiLiquidacion.tsx`.
- Portería: `pages/porteria/VentaRifa.tsx` (pantalla de venta rápida), con inicio en `/porteria`.
- `Usuarios.tsx`: campo teléfono.

**Sin impacto** en boletas, lecturas, liquidaciones, OCR ni el Motor EnerCheck.
