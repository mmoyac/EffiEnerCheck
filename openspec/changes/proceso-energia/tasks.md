# Tasks

## 1. Visibilidad al publicar

- [x] 1.1 `endpoints/liquidaciones.py`: para el rol comunero, el listado filtra por `boleta_visible_usuarios` y la consulta por id responde 403 «La liquidación aún no está publicada» si el período no está publicado. Ajustar los tests que suponían visibilidad al cierre. Verificar con pytest los escenarios del delta de `portal-parcelero`.

## 2. Aceptación de punta a punta

- [x] 2.1 `tests/test_proceso_energia.py`: recorre por la API el escenario «Recorrido completo» de `proceso-energia`:
  1. lectura inicial por Excel;
  2. cierre;
  3. primera boleta con lectura anterior heredada;
  4. totales a mano sin imagen;
  5. corroboración;
  6. toma del lector por sincronización con foto;
  7. cierre de lecturas;
  8. cálculo cuadrado al peso;
  9. cierre del período;
  10. el comunero no ve nada antes de publicar;
  11. publicación;
  12. el comunero ve solo lo suyo y su foto;
  13. el segundo período hereda lecturas y cargos.

  Verificar con la suite completa en verde.

## 3. Documentación

- [x] 3.1 `docs/flujo-periodo.md` (el comunero ve lo publicado; enlace a la spec `proceso-energia`) y `CLAUDE.md` (la spec en la tabla de OpenSpec). Verificar con `openspec validate proceso-energia --strict`.
