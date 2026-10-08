# Proposal

## Why

La presentación a la comunidad dejó tres ajustes. Primero, el término «parcelero» no es el que usa la comunidad: allí se habla de **comuneros**. Segundo, quien compra números desde su portal hoy recibe solo una línea de texto, sin un resumen claro de lo que compró ni un agradecimiento por su aporte solidario. Tercero, no existe material para capacitar a quienes usan la plataforma. Eso incluye a vecinos, portería, administración y también al futuro administrador externo, que no es parte de la comunidad y gestionará las boletas de energía.

## What Changes

- **BREAKING** El rol `parcelero` pasa a llamarse `comunero` en todo el sistema:
  - una migración renombra el valor en la tabla `roles` (mismo id 4, los usuarios conservan su rol);
  - también cambian las guardas, el código, los textos de pantalla, los tests, la documentación y las specs.

  Cualquier integración o script que busque el rol por su nombre `parcelero` deja de encontrarlo.
- Al confirmar una compra de rifa desde el portal, el comunero ve una **pantalla de agradecimiento** con:
  - el folio, los números, la parcela y el total;
  - lo que sigue según la forma de pago: datos para transferir y aviso de pago pendiente, o aviso de cargo en el próximo gasto común;
  - las acciones para guardar o compartir el comprobante y para volver a la rifa.
- Nuevo **centro de capacitación de EFFIComunidad**:
  - es una página estática y pública en `/capacitacion/` del portal: no requiere sesión, no consulta la API y usa solo datos simulados;
  - se organiza por módulo y por rol, con recorridos animados que imitan las pantallas reales;
  - en esta entrega cubre por completo el módulo de **Rifas**, con sus tres caminos de compra: portería, administración desde su menú y el comunero desde su portal;
  - presenta la plataforma y deja como «próximamente» las secciones de Núcleo (acceso, usuarios, parcelas) y Energía;
  - se enlaza desde el Login («¿Primera vez? Mira cómo funciona») y desde una opción «Ayuda» del portal.

## Capabilities

### New Capabilities
- `capacitacion-plataforma`: centro de capacitación público y transversal de la plataforma (acceso sin sesión, ausencia de datos reales, organización por módulo y rol, recorridos animados, obligación de mantenerlo al día cuando cambia un flujo o se agrega un módulo).

### Modified Capabilities
- `control-acceso-multitenant`: el rol `parcelero` se renombra `comunero` en la jerarquía de roles, en las guardas y en la pantalla de inicio por rol. El resto de las menciones al término en las specs se actualiza en el barrido terminológico del archivado (ver design).
- `rifas-solidarias`: la compra desde el portal termina en una pantalla de agradecimiento con el resumen de lo comprado y los pasos siguientes según la forma de pago. La capacidad hoy está en el cambio `rifas-solidarias`, aún sin archivar.

## Impact

- **Base de datos:** migración Alembic que ejecuta `UPDATE roles SET nombre='comunero', descripcion=... WHERE id=4`, con su reversa. Seeds de roles y menús.
- **Backend:** `core/dependencies.py` (`ROLES`, `AnyRoleRequired`), los filtros por parcela de `boletas.py`, `lecturas.py`, `liquidaciones.py` y `parcelas.py`, y los scripts de producción `cargar_residentes.py` y `copiar_desde_desarrollo.py`, junto con sus tests.
- **Frontend:** `hooks/useAuth.ts`, `config/inicio.ts`, `Header.tsx`, `Usuarios.tsx`, `App.tsx`; la carpeta `pages/parcelero/` pasa a `pages/comunero/`; `CompraPanel.tsx` (modo portal) y un componente nuevo de agradecimiento; enlaces a la capacitación en `Login.tsx` y en el menú.
- **PWA:** `/capacitacion/` se excluye del `navigateFallback` del service worker; si no, el SW serviría el portal en lugar de la capacitación.
- **Contenido nuevo:** `frontend/public/capacitacion/` (HTML, CSS y JS estáticos, sin dependencias externas).
- **Docs:** `CLAUDE.md`, `AGENTS.md`, `README.md`, `DEPLOY.md`, `docs/*`, `schema.dbml`; la spec `portal-parcelero` pasa a `portal-comunero`.
- **Sesiones abiertas:** el rol se resuelve desde la base en cada petición, así que no hay que invalidar los JWT. La sesión guardada en el navegador se refresca con `/auth/me`.
- **Orden de archivado:** este cambio se archiva **después** de los cambios en curso que mencionan `parcelero` (`rifas-solidarias`, `medios-pago-por-rifa`, `eliminar-rifa`, `acceso-por-invitacion`, entre otros).
