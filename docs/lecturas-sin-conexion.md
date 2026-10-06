# Toma de lecturas sin señal

La app de lecturas funciona **sin conexión**: el lector recorre las parcelas sin señal y sincroniza al volver. El resto del portal (rifas, administración, liquidaciones) sigue requiriendo conexión.

## Para el lector

1. **Instala la app** en el celular, una vez: en Chrome, menú ⋮ → *Agregar a pantalla de inicio*; en iPhone (Safari), botón Compartir → *Agregar a inicio*. En iPhone es importante: si no se instala, Safari puede borrar los datos de sitios que no se usan en 7 días.
2. **Antes de salir, con señal:** abre la app. Si es la primera vez, presiona **Preparar recorrido**. Arriba verás "Recorrido de las hh:mm".
3. **En terreno:** toma las lecturas como siempre. Sin señal aparece la barra amarilla *"Sin conexión: las lecturas se guardan en el celular · N sin sincronizar"*, y cada parcela muestra "en el celular, sin sincronizar".
4. **Al volver la señal:** se sincroniza sola. También puedes presionar **Sincronizar**.
5. Si aparece la pestaña **Revisar** ⚠️, alguna lectura no se aplicó. El motivo aparece en la parcela:
   - *"cambió en el servidor después de preparar el recorrido"*: alguien la registró o corrigió mientras tanto. Entra a la parcela y vuelve a capturarla si corresponde, o presiona **Descartar** para quedarte con la del servidor.
   - *"las lecturas del período ya están cerradas"*: avisa a la administración.

Las lecturas **no se pierden** si se cierra la app, se apaga el celular o vence la sesión. Si la sesión venció, la app pide la clave y sincroniza después. **No borres los datos del navegador** mientras haya lecturas sin sincronizar.

## Cómo funciona (técnico)

- **IndexedDB** (`efficomunidad-lecturas`), en `frontend/src/offline/lecturas.ts`:
  - `recorrido`: período, parcelas y lecturas como **base**;
  - `pendientes`: lecturas tomadas que el servidor aún no confirma.
- **`POST /api/v1/lecturas/sincronizar`** (rol lector y administrativos): lote de hasta 200 lecturas `{lectura_id, lectura_actual, fecha_toma, base}`. Cada una responde `aplicada`, `conflicto` (la del servidor ya no coincide con la base; no se pisa) o `rechazada` (período cerrado, contador regresivo u otro condominio). Es idempotente: reenviar lo ya aplicado responde `aplicada` sin auditar de nuevo.
- **Sesión sin señal:** `AuthContext` guarda la última sesión (`localStorage.sesion`). Si `/auth/me` falla **por red**, la usa; si el servidor responde 401, la sesión se cierra como siempre.
- **Probar en desarrollo:** Chrome DevTools → *Application → Service Workers* (debe estar activo) y *Network → Offline*.
