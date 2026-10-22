# Documentación de EnerCheck

| Documento | Para quién | Contenido |
|-----------|-----------|-----------|
| [ayuda-energia.md](ayuda-energia.md) | Quien escriba la ayuda / capacitación | Módulo Energía por rol y paso (incorporación, mes, lector, comunero), glosario, preguntas frecuentes, mensajes y recorridos sugeridos para `recorridos/energia.js`. |
| [flujo-periodo.md](flujo-periodo.md) | Equipo técnico | El ciclo mensual completo: los 11 pasos, endpoints, candados, códigos de error y reversas. |
| [flujo-periodo.html](flujo-periodo.html) | Presentación | La misma información en formato visual. Se abre directo en el navegador, sin servidor. |
| [presentacion-comunidad.md](presentacion-comunidad.md) | Comunidad Santa Laura | Documento para la reunión de copropietarios. |
| [rifas.md](rifas.md) | Equipo técnico | Rifas solidarias: flujo, reglas, endpoints y pantallas. Se cobran aparte de la boleta eléctrica. |
| [pagos-en-linea.md](pagos-en-linea.md) | Equipo técnico | Pasarelas de pago (Flow, Khipu): configuración, comisión, estados, reglas del flujo, sandbox y cómo agregar un proveedor. |
| [/capacitacion/](../frontend/public/capacitacion/index.html) | Todos los usuarios | Centro de capacitación de EFFIComunidad: recorridos animados por módulo y rol (Energía y Rifas). Público en `/capacitacion/` del portal; fuentes en `frontend/public/capacitacion/`. |
| [plantilla-onboarding-comuneros.xlsx](plantilla-onboarding-comuneros.xlsx) | Administración de un condominio nuevo | Lo mínimo para crear los accesos de los comuneros (unidad, nombre, rol, correo, teléfono). La carga tal cual `python -m app.db.cargar_residentes`. Ya completada tiene datos personales: va a `docs/planillas/` (ignorada), nunca al repo. |
| [plantilla-onboarding-backoffice.xlsx](plantilla-onboarding-backoffice.xlsx) | Administración de un condominio nuevo | Datos del condominio y cuentas del equipo: administración, lector de medidores y portería. Estas cuentas se crean a mano en Usuarios. Misma regla de datos personales. |
| [sitio-publico.md](sitio-publico.md) | Equipo técnico | Landing pública del condominio: contrato, secciones, cómo editar el contenido y plan para editarlo desde el portal. |

## Dónde vive el resto

La documentación de EnerCheck está repartida por propósito, no toda en esta carpeta:

| Ubicación | Qué contiene |
|-----------|--------------|
| [../README.md](../README.md) | Presentación del proyecto, instalación y stack. Punto de entrada en GitHub. |
| [../CLAUDE.md](../CLAUDE.md) | Guía operativa para agentes de IA: arquitectura, patrones, comandos, errores conocidos. |
| [../AGENTS.md](../AGENTS.md) | Contexto de producto: objetivo, identidad visual, decisiones de diseño. |
| [../openspec/specs/](../openspec/specs/) | Qué hace el sistema hoy, capacidad por capacidad, en requisitos y escenarios. |
| [../openspec/changes/](../openspec/changes/) | Cambios propuestos y en curso. |
| [../schema.dbml](../schema.dbml) | Esquema de base de datos. |

`README.md`, `CLAUDE.md` y `AGENTS.md` se quedan en la raíz a propósito: las herramientas y los agentes los buscan ahí.

## Mantener esto al día

[flujo-periodo.md](flujo-periodo.md) describe el flujo **con el cambio `items-credito-y-validacion` aplicado**, que todavía no está implementado. Cuando ese cambio se archive, revisar que el documento siga coincidiendo con las specs y quitar las marcas de *nuevo* y *cambia*.
