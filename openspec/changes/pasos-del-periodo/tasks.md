# Tasks

## 1. Consola

- [x] 1.1 `utils/pasosPeriodo.ts`: los pasos del período (regular y lectura inicial), cuáles están hechos y el siguiente, a partir de la boleta, las lecturas tomadas y las liquidaciones. Verificar con `npm run build`.
- [ ] 1.2 `BoletaDetalle.tsx`:
  - barra de pasos con ✓, el paso actual resaltado y la línea «Siguiente paso»;
  - solo el botón del siguiente paso en verde y el resto en gris;
  - botón «Ingresar datos de la boleta» cuando faltan los totales;
  - las lecturas se consultan siempre, para mostrar el avance.

  Verificar en el navegador cada escenario del delta de `consola-administrativa`.

- [ ] 1.3 `LectorDashboard.tsx`: aviso «Las lecturas de … están cerradas…» cuando el período del recorrido tiene las lecturas cerradas. Verificar en el navegador como lector, con un período cerrado.

- [ ] 1.4 `Boletas.tsx`: quitar los atajos del ciclo de cada fila (cerrar lecturas, calcular, publicar) y agregar «Continuar» hacia el detalle. Verificar en el navegador.

- [x] 1.5 Backend: `services/periodos.descartar_liquidaciones()` al reabrir lecturas, editar el desglose, reprocesar con IA, y crear, corregir o sincronizar (aplicada) una lectura; `liquidaciones_descartadas` en la auditoría. El frontend refresca las liquidaciones tras esas acciones. Verificado con `tests/test_liquidaciones_vigentes.py` (reabrir, desglose, corrección, sincronización, reintento sin cambios) y la suite completa en verde.

## 2. Documentación

- [x] 2.1 `docs/ayuda-energia.md`: la barra de pasos como guía del administrador. Verificar con `openspec validate pasos-del-periodo --strict`.
