# Design

- **`rifas.medios_pago`:** `VARCHAR[]` con `server_default` de las tres formas. El CHECK exige que no esté vacío y que solo contenga valores del catálogo. El orden se normaliza al del catálogo.
- **Validación:** se hace en `POST /compras`, después de las reglas de canal y antes de reservar los números.
- **Sin efecto retroactivo:** el cierre sigue imputando las compras `gasto_comun` existentes aunque la rifa ya no acepte esa forma.
