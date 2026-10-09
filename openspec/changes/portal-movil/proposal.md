# Proposal

## Why

La administración, el lector y el comunero usan el portal sobre todo desde el **celular**. Varias pantallas muestran tablas anchas:
- algunas obligan a desplazarse en horizontal: Boletas, el detalle del período, el Panel y Rifas;
- otras desbordan la página completa: Parcelas y Usuarios.

Además, hubo ventanas (modales) más altas que la pantalla, con los botones de acción fuera de vista. Antes de salir a producción, el portal tiene que poder usarse cómodo en cualquier celular.

## What Changes

- **Sin scroll horizontal en el celular.** En pantallas angostas, cada tabla de más de tres columnas se muestra como una **lista apilada**, con una tarjeta por registro, los mismos datos y las mismas acciones. Desde `md` se mantiene la tabla.
  - Pantallas: Boletas, el detalle del período (lecturas, con su edición en línea, y liquidaciones), el Panel, Parcelas (con su alta y edición en línea), Usuarios, Rifas, el detalle de una rifa y la caja.
- **Ventanas acotadas a la pantalla:** el componente `Modal` nunca supera la altura del dispositivo; el contenido hace scroll vertical interno y nunca horizontal.
- **Listas largas acotadas en altura** dentro de las ventanas (vista previa del Excel, cuenta de una parcela).
- **Barras de botones y filtros** que se acomodan (`flex-wrap`).
- Sin cambios de comportamiento, de datos ni de API.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `consola-administrativa`: el portal se usa en el celular sin scroll horizontal y con ventanas acotadas a la pantalla.

## Impact

- **Frontend:**
  - `components/ui/Modal.tsx`;
  - `pages/admin/Boletas.tsx`, `BoletaDetalle.tsx`, `Dashboard.tsx`, `Parcelas.tsx`, `Usuarios.tsx`, `Rifas.tsx`, `RifaDetalle.tsx`;
  - `components/rifas/CajaResumen.tsx`;
  - `ImportarLecturasIniciales.tsx` y `Cobranza.tsx`, que ya siguen la regla.
- **Docs:** `CLAUDE.md` (la regla, en los patrones de frontend).
