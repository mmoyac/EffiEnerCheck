## MODIFIED Requirements

### Requirement: Vocabulario de acciones

Cada registro DEBE (SHALL) identificar la acción mediante un código en mayúsculas con guiones bajos. El vocabulario en uso comprende `UPLOAD_BOLETA`, `UPDATE_BOLETA`, `TOGGLE_VISIBILITY`, `UPLOAD_IMAGEN_BOLETA`, `PROCESS_OCR`, `UPDATE_DETALLES_BOLETA`, `DELETE_BOLETA`, `VALIDAR_ITEMS`, `CERRAR_LECTURAS`, `REABRIR_LECTURAS`, `CERRAR_LIQUIDACIONES`, `REABRIR_LIQUIDACIONES`, `CREATE_LECTURA`, `UPDATE_LECTURA`, `CALCULAR_LIQUIDACIONES`, `MARCAR_PAGO`, `CREATE_PARCELA`, `UPDATE_PARCELA`, `CREATE_USER`, `UPDATE_USER` y `DELETE_USER`.

#### Scenario: Distinción entre actualización y publicación

- **WHEN** una actualización de boleta incluye el campo `boleta_visible_usuarios`
- **THEN** la acción se registra como `TOGGLE_VISIBILITY`, y como `UPDATE_BOLETA` en caso contrario

#### Scenario: Corroboración del desglose

- **WHEN** un administrador corrobora los ítems de una boleta
- **THEN** la acción se registra como `VALIDAR_ITEMS`

## ADDED Requirements

### Requirement: Instantánea del desglose corroborado

El registro de la acción `VALIDAR_ITEMS` DEBE (SHALL) incluir en sus detalles una copia del desglose en el instante de la corroboración: la descripción, el monto y el `tipo_calculo` de cada ítem, junto con los totales de la boleta.

#### Scenario: Prueba de lo que se decidió

- **WHEN** meses después se cuestiona por qué un cargo entró o no entró al reparto de un período
- **THEN** el registro permite demostrar qué ítems existían, con qué montos, cómo fueron clasificados, quién lo decidió y cuándo

#### Scenario: Corroboraciones sucesivas

- **WHEN** una boleta vuelve a `borrador` y se corrobora nuevamente tras corregir el desglose
- **THEN** cada corroboración deja su propio registro con su propia instantánea, sin sobrescribir las anteriores
