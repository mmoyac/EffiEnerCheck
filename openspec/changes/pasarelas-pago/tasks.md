# Tasks

## 1. Modelo y cifrado

- [x] 1.1 Agregar `cryptography` a `requirements.txt`, reconstruir el backend y verificar `import cryptography` en el contenedor y `pip-audit` limpio.
- [x] 1.2 Modelos `PasarelaPago` e `IntencionPago`, `compras_rifa.intencion_pago_id`, `en_linea` en `MEDIOS_PAGO` y el CHECK de `rifas.medios_pago`, y el menú "Pasarelas de pago" (Administración, roles admin), con su migración y `downgrade`. Actualizar `schema.dbml`. Verificar con `alembic upgrade head` y `alembic downgrade -1`.
- [x] 1.3 `services/pagos/cifrado.py` (AES-256-GCM, AAD `condominio:<id>:pasarela:<id>`), `PAGOS_CLAVE_MAESTRA` y `URL_PUBLICA_PAGOS` en `config.py`, validación de la clave en `app.arranque` (producción) y el comando `python -m app.db.rotar_clave_pagos`. Verificar con pytest:
  - ida y vuelta;
  - AAD distinta = no descifra;
  - la rotación conserva los valores;
  - el arranque de producción falla sin la clave.

## 2. Contrato y adaptadores

- [x] 2.1 `services/pagos/proveedores/base.py` (`Adaptador`, `Redireccion`, `Resultado`, `CampoCredencial`, errores) y `services/pagos/comision.py`. Verificar con pytest los ejemplos de la spec ($6.000 al 3,8 % = $6.238; comisión 0 = mismo monto).
- [x] 2.2 Adaptador Flow con `httpx` inyectable. Verificar con pytest y `httpx.MockTransport`:
  - el vector de firma;
  - `crear` (con `timeout` y sin `optional`);
  - los estados 1, 2, 3 y 4;
  - los errores 400 y 401;
  - la prueba de conexión (1700 = OK; "apiKey not found" = credenciales);
  - el filtrado de la respuesta.
- [x] 2.3 Adaptador Khipu. Verificar con pytest y `MockTransport`:
  - `crear` con y sin `notify_url` según https;
  - `return_url` y `cancel_url` con la intención;
  - `done`+`normal` = aprobado; `verifying` = pendiente; `rejected-by-payer` y `reversed` = rechazado; desconocido = pendiente;
  - la prueba de conexión (200, 401, 403);
  - `anular` (2xx = True; error = False).

## 3. Pasarelas (administración)

- [x] 3.1 `endpoints/pasarelas.py` (escritura solo `super_admin`; lectura también `admin_condominio`, sin credenciales):
  - catálogo de proveedores;
  - CRUD con aislamiento por condominio;
  - reemplazo de credenciales (desactiva la pasarela);
  - cambio de ambiente (desactiva la pasarela);
  - probar, activar y desactivar (producción exige una prueba exitosa posterior a `credenciales_at`);
  - eliminar solo sin intenciones;
  - auditoría sin valores.

  Verificar con pytest cada escenario de la spec, incluido que ninguna respuesta ni registro de auditoría contiene un secreto.
- [x] 3.2 Página `admin/Pasarelas.tsx`:
  - lista apilada en celular;
  - selector de condominio para el `super_admin`;
  - solo lectura para el `admin_condominio`;
  - modal con formulario dinámico (secretos `type=password`, nunca precargados);
  - probar, activar y desactivar;
  - ruta y menú.

  Verificar en el navegador a 390 px: el `super_admin` crea una pasarela de integración, la prueba y la activa; el `admin_condominio` la ve sin acciones.

## 4. Flujo de pago y endpoints públicos

- [x] 4.1 Registro de consumidores y `services/rifas_pago.py` (`aplicar`, `liberar`, `descripcion`), con la reactivación de una compra anulada si sus números siguen libres y la rifa sigue abierta. Verificar con pytest:
  - aplicar sobre una compra pendiente;
  - liberar;
  - reactivar;
  - números ya vendidos → motivo de revisión.
- [x] 4.2 `services/pagos/flujo.py`: `iniciar` (commit antes de llamar al proveedor; si falla → `RECHAZADO` + liberar), `confirmar` (consulta sin transacción y luego `FOR UPDATE`), `cancelar` y `expirar`. Verificar con pytest contra Postgres y un adaptador doble:
  - un solo pago con retorno + webhook concurrentes;
  - monto distinto → `EN_REVISION`;
  - rechazo definitivo libera;
  - pago tardío aplicable y no aplicable;
  - un `RECHAZADO` no acepta un aprobado.
- [x] 4.3 `medios_permitidos(rifa, canal, hay_pasarela)`. `POST /rifas/{id}/compras` valida contra ella (422 con una forma no permitida para el canal; voucher obligatorio en la transferencia del portal) y acepta `en_linea` con `pasarela_id` (422 con pasarelas de integración en producción; 409 si ya tiene una intención vigente en esa rifa), devolviendo `redireccion`. `confirmar-pago` y la anulación por el comunero responden 409 con una intención en curso, y `cerrar` responde 409 si hay pagos en curso. Verificar con pytest cada escenario del delta `rifas-solidarias`.
- [x] 4.4 `endpoints/pagos.py`:
  - `GET /pagos/disponibles` (filtro por ambiente y mínimo, con el motivo);
  - `GET /pagos/{id}` y `POST /pagos/{id}/consultar` (dueño o admin; 429 antes de 10 s);
  - retorno GET/POST y webhook (formulario y JSON; búsqueda local antes de llamar al proveedor; 303 al resultado; webhook 200/404);
  - cancelación de Khipu;
  - `GET /pagos/revision` y `POST /pagos/{id}/resolver`.

  Verificar con pytest:
  - un token inventado no llama al proveedor;
  - una intención de otro condominio no se procesa;
  - `?intencion=` con otro proveedor → 404;
  - cancelación con y sin anulación posible.
- [x] 4.5 nginx: zona `enercheck_pagos` y `location` para `/api/v1/pagos/(retorno|webhook)/` en `frontend/nginx.prod.conf`; `.env.prod.example` y `DEPLOY.md` con `PAGOS_CLAVE_MAESTRA`. Verificar con `nginx -t` en la imagen de producción.

## 5. Conciliación

- [x] 5.1 `services/pagos/conciliacion.py`: vuelta con `pg_try_advisory_lock`, selección `INICIADO` > 5 min y `EXPIRADO` < 24 h, aislamiento de errores por intención, bucle en el `lifespan` (apagable con `PAGOS_CONCILIACION=0`). Verificar con pytest:
  - un aviso perdido se confirma;
  - una intención vencida y pendiente pasa a `EXPIRADO` y libera los números;
  - con el candado tomado, la vuelta no hace nada.

## 6. Pantallas del comunero

- [x] 6.1 `CompraPanel` (portal): "Pago en línea" (con el aviso de costo adicional) y "Gasto común"; al elegir en línea, la selección de pasarela con el total de cada una, o directo si hay una sola; redirección GET o formulario POST; sin pasarela disponible, "Transferencia" manual con voucher obligatorio en lugar de "Pago en línea". La portería y la administración no cambian. Verificar en el navegador a 390 px con cero, una y dos pasarelas activas.
- [x] 6.2 `pages/pagos/Resultado.tsx` en `/pagos/:id/resultado`: los cinco estados, consulta cada 3 s, `consultar` cada 15 s durante 5 min y botón "Consultar de nuevo". Verificar en el navegador con una intención en cada estado (forzando el estado en la base de desarrollo).
- [x] 6.3 Sección "Pagos por revisar" en `Pasarelas.tsx` (lista y resolver con nota). Verificar en el navegador con una intención `EN_REVISION`.

## 7. Documentación y capacitación

- [x] 7.1 `docs/pagos-en-linea.md` (configuración, comisión, sandbox de Flow, DemoBank de Khipu, túnel con `URL_PUBLICA_PAGOS`), `docs/rifas.md`, `docs/README.md` y la sección de pagos en `CLAUDE.md`. Verificar que los enlaces abren.
- [x] 7.2 Centro de capacitación: paso "Pago en línea" en el recorrido de rifas del comunero y un recorrido de administración "Configurar una pasarela", con datos ficticios. Verificar abriendo `/capacitacion/` y recorriendo ambos.

## 8. Integración

- [x] 8.1 Suite completa en verde (`pytest`, `npm run build`, `npm audit --omit=dev --audit-level=high`, `pip-audit`) y `openspec validate pasarelas-pago --strict`.
- [ ] 8.2 Prueba manual de punta a punta con túnel `cloudflared`: Flow sandbox (tarjeta `4051885600446623`) y Khipu DemoBank (clave `1234`). Verificar en la base que cada pago deja una intención `CONFIRMADO` y una sola compra pagada, y que un pago abandonado vence y libera los números.
  - Khipu (DemoBank) verificado el 2026-10-13: cobro, cancelación anulada en Khipu y pago aprobado después del retorno confirmado por la conciliación (una sola compra pagada). Pendiente: Flow sandbox.
