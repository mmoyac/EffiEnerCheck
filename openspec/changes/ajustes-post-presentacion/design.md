# Design

## Context

Ver proposal.md (Why). Datos del estado actual que condicionan el enfoque:

- El rol vive en `roles` con id fijo (4 = `parcelero`). El seed `seed_roles` inserta por id y **salta los que ya existen**, así que cambiar el seed no renombra nada en una base existente: solo una migración lo hace.
- El rol se resuelve desde la base en cada petición (`get_current_user` carga `Usuario.rol`). Aunque el JWT lleva un claim `rol`, las guardas no lo usan, así que no hace falta invalidar sesiones.
- El nombre literal `'parcelero'` aparece en unos 15 lugares de código:
  - backend: guardas, filtros por parcela de 4 endpoints y los scripts de carga de producción;
  - frontend: `useAuth`, `inicio.ts`, `Header`, `Usuarios`.

  A eso se suman textos, docs, tests, 7 specs de la línea base y varias deltas de cambios aún sin archivar.
- La compra del portal ocurre en `CompraPanel` (modo `portal`), dentro de `DetalleRifa` de `pages/parcelero/Rifas.tsx`. Hoy el éxito es solo un `Alert` con una línea. Portería ya tiene `ComprobanteVenta`, con folio grande, impresión y WhatsApp.
- El portal es una PWA. El service worker precachea `**/*.html` y su `navigateFallback` devuelve `index.html` para toda navegación salvo `/api/` y `/uploads/`. Sin un ajuste, el SW serviría el portal en `/capacitacion/`.
- El portal en producción (nginx) no tiene CSP. `location /` hace `try_files $uri $uri/ /index.html`, así que una carpeta estática con `index.html` se sirve tal cual. El contenedor de desarrollo también sirve el build con nginx.
- `Header` lo usan `AppLayout` (admin), las páginas del comunero y la portería. La vista del lector (`LectorDashboard`) no lo usa.

## Goals / Non-Goals

**Goals:**
- Que el nombre del rol quede consistente en toda la base, el código y la documentación, sin perder usuarios ni sesiones.
- Una pantalla de agradecimiento que se arme con la respuesta del servidor y reutilice el formato del comprobante.
- Un centro de capacitación que se pueda extender a nuevos módulos y roles agregando datos, sin tocar el motor de recorridos.

**Non-Goals:**
- No renombrar `usuario_parcelas`, `parcela_id` ni nada relacionado con *parcela*: el cambio es solo el nombre del rol.
- No reescribir las migraciones históricas ni los cambios ya archivados en `openspec/changes/archive/`, que quedan como registro.
- No enviar correo ni WhatsApp automático tras la compra: compartir sigue siendo una acción de la persona.
- No escribir todavía los recorridos de Núcleo ni de Energía: quedan como «próximamente».

## Decisions

### D1. Renombrar la fila existente (id 4) con una migración de datos

La migración Alembic ejecuta `UPDATE roles SET nombre='comunero', descripcion='Vecino de una parcela: consulta sus liquidaciones y compra rifas' WHERE id=4 AND nombre='parcelero'`. Su `downgrade` hace la operación inversa. El seed `roles.py` pasa a declarar `comunero` para las bases nuevas.

- *Alternativa descartada:* crear un rol 6 `comunero` y mover a los usuarios. Exige reasignar `usuarios.rol_id` y `menu_roles`, deja un rol huérfano y no aporta nada.
- *Alternativa descartada:* conservar `parcelero` como clave interna y cambiar solo la etiqueta. El usuario pidió el cambio completo para no tener dos nombres para lo mismo.

### D2. Renombre en código: literal, identificadores y carpeta

- Se cambian el literal, los identificadores derivados (`rol_parcelero` → `rol_comunero`, `esParcelero` → `esComunero` o similar) y la carpeta `frontend/src/pages/parcelero/` → `pages/comunero/`.
- En textos para personas, «parcelero(s)» pasa a «comunero(s)».
- Las rutas URL (`/liquidaciones`, `/mis-rifas`) no cambian.
- El criterio de término: `grep -ri parcelero` sobre `backend/app`, `backend/tests`, `frontend/src`, `docs`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `DEPLOY.md`, `schema.dbml` y `.env.prod.example` debe quedar vacío. Solo se exceptúan las migraciones antiguas y la nueva migración.

### D3. Sesión guardada con el nombre antiguo

`AuthContext` usa la sesión guardada en `localStorage` cuando `/auth/me` no responde (sin red). Una sesión guardada antes del despliegue diría `parcelero` y `inicio.ts` no la reconocería. Por eso, al leer la sesión guardada, se normaliza `parcelero` → `comunero`. Es un shim de una línea, comentado como transitorio. Con red, `/auth/me` ya devuelve el nombre nuevo.

### D4. Barrido terminológico de las specs al archivar

Las deltas de OpenSpec no pueden expresar «reemplaza este término en todas las specs». Por eso:

- este cambio modifica formalmente solo los requisitos que **definen** el rol (`control-acceso-multitenant`: jerarquía, guardas e inicio);
- al archivar, una tarea hace el barrido de `parcelero` → `comunero` en `openspec/specs/**` y renombra la carpeta `portal-parcelero` → `portal-comunero`, con el título y el propósito ajustados;
- se valida con `openspec validate --specs --strict`.

Como varios cambios sin archivar (`rifas-solidarias`, `medios-pago-por-rifa`, `eliminar-rifa`, `acceso-por-invitacion`, `lecturas-sin-conexion`, `plataforma-comunidad-landing`, `items-credito-y-validacion`, `migrar-produccion-dokploy`, `app-instalable-por-condominio`) traen deltas con `parcelero` y algunos modifican los mismos requisitos, **este cambio se archiva último**. Así, el barrido cubre todo lo que esos cambios incorporen a la línea base.

### D5. Agradecimiento: estado en la página, componente propio

- `CompraPanel` ya llama a `onVendida(compra)` con la compra que devuelve el servidor. En modo portal deja de mostrar su `Alert` de éxito.
- `DetalleRifa` guarda `compraReciente`. Si existe, muestra `<AgradecimientoCompra rifa compra onComprarMas onVolver>` en lugar de la tarjeta de compra y hace scroll arriba. El componente vive en `components/rifas/`.
- **Contenido:**
  - encabezado con «¡Gracias por tu aporte!» y el beneficiario;
  - bloque de comprobante con el formato de `ComprobanteVenta` (folio grande, números, parcela, monto, forma de pago, fecha);
  - bloque «Qué sigue» según `medio_pago`, con `rifa.datos_transferencia` o, si no hay, el texto «la administración te hará llegar los datos de pago».
- **Acciones:**
  - «Compartir»: `navigator.share` con `mensajeComprobante(rifa, compra)`; si no está disponible, se abre WhatsApp con el texto y sin destinatario;
  - «Guardar» (`window.print()`, reutilizando `.area-impresion`);
  - «Comprar más números» limpia `compraReciente`;
  - «Volver a rifas».
- *Alternativa descartada:* un `Modal`. En el celular tapa la grilla y se cierra con un toque fuera, cuando lo que se quiere es que la persona lea el «qué sigue». Además, una pantalla permite imprimir el comprobante solo.

### D6. Capacitación: sitio estático sin build en `frontend/public/capacitacion/`

Vite copia `public/` tal cual, así que el sitio queda en `/capacitacion/` en desarrollo y en producción, sin contenedor ni dominio nuevos. Estructura:

```
capacitacion/
├── index.html        # Portada EFFIComunidad + navegación por módulo (hash: #rifas/porteria)
├── estilos.css       # Tokens (verde EFFIComunidad #22C55E), tema claro/oscuro, marco de celular simulado
├── motor.js          # Reproductor de recorridos: pasos, play/pausa/atrás/adelante/reiniciar, reduce-motion
└── recorridos/
    ├── plataforma.js # Productos, roles, módulos (con estado: disponible | proximamente)
    └── rifas.js      # Los 3 recorridos: porteria, administracion, comunero
```

- **Recorridos como datos.** Cada paso declara la pantalla simulada (un HTML que imita el portal), el elemento a resaltar, la acción animada (toque, escritura, aparición) y el texto explicativo. El motor no sabe de rifas, así que agregar Energía es agregar `recorridos/energia.js` y registrarlo en `plataforma.js`.
- **Animación** con transiciones CSS y un indicador de toque (un círculo que se desplaza y pulsa). Sin librerías ni recursos externos, en línea con el requisito de no cargar nada de terceros.
- **Pantallas simuladas** con datos ficticios: condominio «Los Aromos», parcelas y nombres inventados, teléfono `+56 9 0000 0000`. La paleta es la del portal, con el verde por defecto, y no lleva marca de ningún condominio porque la capacitación es transversal.
- **Accesibilidad:** el texto del paso va en `aria-live="polite"`, los controles responden al teclado (←, →, espacio) y `prefers-reduced-motion` desactiva las transiciones.
- *Alternativa descartada:* una ruta React del portal. Quedaría acoplada al bundle y al login, sería más difícil de mover a un dominio propio de EFFIComunidad y haría que cualquier cambio del portal pudiera romperla.
- *Alternativa descartada:* un artifact de claude.ai. No se versiona con el código, así que no puede cumplir el requisito de mantenerse al día con el producto.

### D7. PWA y enlaces

- **Service worker:** se agrega `/^\/capacitacion\//` a `navigateFallbackDenylist`. El precache de `**/*.html` igual incluye la capacitación, lo que de paso permite verla sin conexión.
- **Login:** bajo el formulario va el enlace «¿Primera vez? Mira cómo funciona», que abre `/capacitacion/` en una pestaña nueva.
- **Ayuda:** un ícono de ayuda en `Header`, visible para todos los roles, que abre `/capacitacion/`. La vista del lector no usa `Header`, así que lleva el mismo enlace en su cabecera propia.
- *Alternativa descartada:* un ítem en la tabla `menus`. Exigiría seed y migración para un enlace estático, y el comunero y la portería no tienen sidebar.

## Risks / Trade-offs

- **[Riesgo]** Un script u operación manual en producción busca el rol por nombre `parcelero`. → Los únicos conocidos son `cargar_residentes.py` y `copiar_desde_desarrollo.py`, que se actualizan aquí. DEPLOY.md documenta el cambio.
- **[Riesgo]** El rollback de la imagen no revierte la base: el frontend o backend antiguos esperarían `parcelero`. → En DEPLOY.md, el procedimiento de rollback de este despliegue incluye `alembic downgrade -1` antes de volver a la imagen anterior.
- **[Riesgo]** Las deltas en curso reintroducen `parcelero` al archivarse. → D4: este cambio se archiva último y su tarea de barrido lo verifica con grep.
- **[Trade-off]** La capacitación simula las pantallas en lugar de usar capturas. Es más liviana, nítida en proyector y no expone datos, pero hay que mantenerla a mano cuando cambia la UI. El requisito «Capacitación al día con el producto» lo hace obligatorio.
- **[Riesgo]** El SW antiguo, ya instalado en los celulares, sigue interceptando `/capacitacion/` hasta que se actualiza. → El SW se actualiza con `skipWaiting` en la siguiente visita al portal. Mientras tanto, el enlace del Login abre en pestaña nueva y la recarga lo resuelve.

## Migration Plan

1. **Desarrollo:**
   - `docker-compose up --build -d backend frontend`, luego `alembic upgrade head` y verificar que `SELECT nombre FROM roles WHERE id=4` devuelva `comunero`;
   - ingresar con `mmoyainfo+parcela@gmail.com`;
   - correr los tests.
2. **Producción**, cuando el usuario lo pida: el despliegue normal (`app.arranque` migra al arrancar). No requiere pasos manuales.
3. **Rollback:** `alembic downgrade -1` (vuelve a `parcelero`) y luego reimplantar la imagen anterior.
