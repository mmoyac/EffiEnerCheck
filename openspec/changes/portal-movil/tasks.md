# Tasks

## 1. Base

- [x] 1.1 `Modal.tsx`: altura máxima de la pantalla y cuerpo con scroll vertical, sin scroll horizontal. Vista previa del Excel y `Cobranza.tsx` con listas apiladas y acotadas. Verificado con `npx tsc --noEmit`.

## 2. Pantallas

- [x] 2.1 `Boletas.tsx` y `Dashboard.tsx`: lista apilada en celular, tabla desde `md`.
- [x] 2.2 `BoletaDetalle.tsx`: lecturas (con edición en línea) y liquidaciones (con total) apiladas en celular; botonera y guía de pasos que se acomodan.
- [x] 2.3 `Parcelas.tsx` (con alta y edición en línea) y `Usuarios.tsx`: lista apilada en celular.
- [x] 2.4 `Rifas.tsx`, `RifaDetalle.tsx` y `CajaResumen.tsx`: lista apilada en celular.
- [ ] 2.5 Verificación: `npm run build` y revisión en el navegador con DevTools en modo celular (por ejemplo, 390 px de ancho), sin scroll horizontal en ninguna pantalla.

## 3. Documentación

- [x] 3.1 `CLAUDE.md`: la regla de UI móvil en los patrones de frontend. Verificar con `openspec validate portal-movil --strict`.
