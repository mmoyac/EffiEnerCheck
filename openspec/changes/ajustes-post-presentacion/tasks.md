# Tasks

## 1. Rol comunero: base de datos y backend

- [x] 1.1 Crear la migración Alembic que renombra el rol id 4 (`parcelero` → `comunero`, con su descripción) y su `downgrade`. Verificar con `alembic upgrade head` + `SELECT nombre FROM roles WHERE id=4` = `comunero`, y `alembic downgrade -1` + `upgrade head` sin errores.
- [x] 1.2 Actualizar `seeds/roles.py`, `seeds/menus.py` y `seeds/usuarios.py` (nombre, descripción, comentarios). Verificar que el seeder corre sobre una base limpia y crea `comunero`.
- [x] 1.3 Renombrar el literal y los identificadores en `core/dependencies.py` (`ROLES`, `AnyRoleRequired` y su comentario), en los filtros de `boletas.py`, `lecturas.py`, `liquidaciones.py` y `parcelas.py`, en los schemas y en `models/`. Verificar que `grep -ri parcelero backend/app --include=*.py` solo encuentra la migración nueva.
- [x] 1.4 Actualizar `db/cargar_residentes.py` y `db/copiar_desde_desarrollo.py` (búsqueda del rol, variables y mensajes). Verificar que pasan `test_carga_produccion.py` y `test_copia_desarrollo.py`.
- [x] 1.5 Actualizar los tests (`test_claves`, `test_enlaces`, `test_lecturas_sin_conexion`, `test_modulos` y los demás que usan el rol). Agregar un test que verifique que un `comunero` solo ve sus parcelas y que `AnyRoleRequired` lo acepta. Verificar con `docker exec enercheck-backend-1 sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"` en verde.

## 2. Rol comunero: frontend

- [x] 2.1 Mover `pages/parcelero/` a `pages/comunero/` y actualizar los imports en `App.tsx`. Verificar con `npm run build` sin errores.
- [x] 2.2 Renombrar el literal en `useAuth.ts`, `config/inicio.ts`, `Header.tsx` (etiqueta «Comunero» y condición del acceso a rifas), `Usuarios.tsx` (lista de roles, colores, comentarios) y `pages/admin/Rifas.tsx`. Revisar también los textos de pantalla «parcelero(s)». Verificar que `grep -ri parcelero frontend/src` queda vacío.
- [x] 2.3 Normalizar `parcelero` → `comunero` al leer la sesión guardada en `AuthContext` (shim transitorio comentado, D3). Verificar: con una sesión guardada a mano con `rol.nombre='parcelero'` y sin red, la app abre `/liquidaciones`.
- [x] 2.4 Probar en desarrollo: ingresar con `mmoyainfo+parcela@gmail.com` lleva a `/liquidaciones`, la cabecera dice «Comunero» y Usuarios muestra y permite asignar el rol «comunero» conservando las parcelas.

## 3. Rol comunero: documentación

- [x] 3.1 Actualizar `CLAUDE.md`, `AGENTS.md`, `README.md`, `DEPLOY.md` (con la nota de rollback: `alembic downgrade -1` antes de volver a la imagen anterior), `docs/*.md`, `docs/flujo-periodo.html`, `schema.dbml` y `.env.prod.example`. Verificar que `grep -ril parcelero` sobre esos archivos queda vacío, salvo la nota histórica de DEPLOY.md.

## 4. Agradecimiento tras la compra desde el portal

- [x] 4.1 Crear `components/rifas/AgradecimientoCompra.tsx` según D5:
  - «¡Gracias por tu aporte!» con el beneficiario;
  - comprobante con folio, números, parcela, monto, forma de pago y fecha;
  - «Qué sigue» por forma de pago, con los datos de transferencia o el texto alternativo cuando la rifa no tiene;
  - acciones Compartir (`navigator.share`, con WhatsApp como alternativa), Guardar (imprimir), Comprar más números y Volver a rifas.

  Verificar con `npm run build`.
- [x] 4.2 En `CompraPanel` (modo portal), quitar el `Alert` de éxito. En `pages/comunero/Rifas.tsx`, guardar `compraReciente` desde `onVendida`, mostrar el agradecimiento en lugar de la tarjeta de compra y hacer scroll arriba. Verificar en desarrollo:
  - compra con gasto común: aviso de cargo;
  - compra por transferencia: datos para transferir y pendiente;
  - «Comprar más»: la grilla vuelve con los números marcados como de la parcela;
  - un 409 sigue mostrando el error sin agradecimiento;
  - la venta en portería sigue mostrando `ComprobanteVenta`.
- [x] 4.3 Actualizar `docs/rifas.md` con la pantalla de agradecimiento. Verificar que la sección de compra desde el portal la describe.

## 5. Centro de capacitación

- [x] 5.1 Crear `frontend/public/capacitacion/` con `index.html`, `estilos.css` y `motor.js`:
  - reproductor con avanzar, retroceder, pausar y reiniciar, y teclas ←, →, espacio;
  - texto del paso en `aria-live`, `prefers-reduced-motion`, tema claro/oscuro y marco de celular simulado.

  Verificar abriendo `/capacitacion/` en el contenedor de desarrollo, a 360 px y a pantalla completa, sin scroll horizontal.
- [x] 5.2 Crear `recorridos/plataforma.js` con la portada de EFFIComunidad (productos: sitio y portal; roles; módulos con estado). Rifas queda `disponible`, y Núcleo y Energía `proximamente`. Verificar que elegir un módulo pendiente muestra «próximamente» y permite volver.
- [x] 5.3 Crear `recorridos/rifas.js` con la explicación de los tres caminos y sus recorridos, todo con datos ficticios:
  - **Portería:** buscar la parcela, elegir números, forma de pago (efectivo o transferencia con voucher), registrar y ver el comprobante con folio y WhatsApp.
  - **Administración:** menú Rifas, detalle, «Registrar compra» a nombre de una parcela y luego confirmar un pago por transferencia.
  - **Comunero:** ingreso con correo y clave, aviso de rifa abierta, grilla, forma de pago, confirmación y agradecimiento.

  Verificar reproduciendo los tres de principio a fin y contrastando cada paso con la pantalla real del portal.
- [x] 5.4 Agregar `/^\/capacitacion\//` a `navigateFallbackDenylist` en `vite.config.ts`. Verificar que, con el portal instalado o con el SW activo, `/capacitacion/` muestra la capacitación y no el portal.
- [x] 5.5 Agregar los enlaces: «¿Primera vez? Mira cómo funciona» en `Login.tsx`, el ícono de ayuda en `Header.tsx` y el enlace en la cabecera de `LectorDashboard`. Verificar que los cuatro tipos de pantalla (admin, comunero, portería, lector) muestran el acceso y que abre `/capacitacion/`.
- [x] 5.6 Verificar en la pestaña de red que la capacitación no hace peticiones a `/api/` ni a dominios de terceros.
- [x] 5.7 Documentar en `CLAUDE.md` (estructura y regla «un flujo visible que cambia actualiza su recorrido; un módulo nuevo agrega su sección») y en `docs/README.md` (enlace a la capacitación). Verificar que ambos mencionan `frontend/public/capacitacion/`.

## 6. Integración y cierre

- [x] 6.1 CI local en verde: `pytest`, `npm run build`, `npm audit --omit=dev --audit-level=high` y `openspec validate ajustes-post-presentacion --strict`.
- [ ] 6.2 Al archivar, **después** de los cambios en curso que mencionan `parcelero`, hacer el barrido terminológico (D4):
  - reemplazar `parcelero` → `comunero` en `openspec/specs/**`;
  - renombrar `openspec/specs/portal-parcelero/` → `portal-comunero/`, con el título y el propósito ajustados.
  - actualizar los enlaces `../portal-parcelero/spec.md` de las demás specs (por ejemplo, `proceso-energia`) a `../portal-comunero/spec.md`. El reemplazo de `parcelero` ya los cubre; confirmarlo con el mismo grep.

  Verificar que `grep -ri parcelero openspec/specs` queda vacío y que pasa `openspec validate --specs --strict`.
