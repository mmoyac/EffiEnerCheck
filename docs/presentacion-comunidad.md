# EnerCheck — Gestión Digital de Cuentas Eléctricas
## Presentación para la Comunidad · Condominio Santa Laura

---

## ¿Cuál era el problema?

Cada mes, el condominio recibe **una sola boleta eléctrica** de la compañía distribuidora que incluye el consumo de todas las parcelas juntas.

Para cobrar a cada comunero lo que realmente consumió, alguien debía:

- Ir físicamente a leer cada remarcador
- Anotar los datos en papel o planilla Excel
- Hacer los cálculos manualmente
- Distribuir la información por teléfono o papel
- Repetir el proceso cada mes

Este proceso era **lento, propenso a errores y poco transparente** para los comuneros.

---

## ¿Qué es EnerCheck?

**EnerCheck es un sistema digital que automatiza todo ese proceso.**

Desde la carga de la boleta eléctrica hasta que cada comunero pueda ver en su celular exactamente cuánto debe pagar ese mes — con el detalle de cómo se calculó su monto.

> *"Del papel a la pantalla, con transparencia total."*

---

## ¿Quiénes participan?

El sistema tiene **4 tipos de usuario**, cada uno con acceso a lo que necesita:

| Quién | Qué hace en EnerCheck |
|-------|----------------------|
| **Administrador** | Carga la boleta eléctrica, revisa liquidaciones, publica resultados |
| **Lector** | Registra las lecturas de cada remarcador desde su celular |
| **Comunero** | Consulta su liquidación y estado de pago desde el celular |
| **Super Admin** | Gestiona múltiples condominios (uso interno del sistema) |

---

## ¿Cómo funciona mes a mes?

El proceso completo toma **menos de 30 minutos** y sigue siempre el mismo orden:

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUJO MENSUAL ENERCHECK                     │
├──────┬──────────────────────────────────────────────────────────┤
│  1   │  ADMIN sube la foto de la boleta eléctrica               │
│      │  → La inteligencia artificial lee los montos             │
│      │    automáticamente (no hay que tipear nada)              │
├──────┼──────────────────────────────────────────────────────────┤
│  2   │  LECTOR recorre las parcelas con su celular              │
│      │  → Registra la lectura de cada remarcador en la app      │
│      │  → Al terminar, confirma que están todas ingresadas       │
├──────┼──────────────────────────────────────────────────────────┤
│  3   │  ADMIN presiona "Calcular"                               │
│      │  → El sistema distribuye el costo automáticamente        │
│      │  → Genera la liquidación individual de cada parcela       │
├──────┼──────────────────────────────────────────────────────────┤
│  4   │  ADMIN revisa los resultados y cierra el período          │
│      │  → Si hay un error, puede corregir una lectura y          │
│        el sistema recalcula todo al instante                    │
├──────┼──────────────────────────────────────────────────────────┤
│  5   │  ADMIN publica                                           │
│      │  → Cada comunero recibe acceso a su liquidación           │
├──────┼──────────────────────────────────────────────────────────┤
│  6   │  COMUNERO consulta desde su celular                      │
│      │  → Ve su monto, el desglose y si ya fue marcado pagado   │
└──────┴──────────────────────────────────────────────────────────┘
```

---

## ¿Cómo se calcula el monto de cada parcela?

El cálculo es **transparente y auditable**. Se compone de tres partes:

### 1. Energía propia (lo que consumió cada parcela)
Basado en la lectura real del remarcador de esa parcela.

### 2. Prorrateo variable
Los cargos de la boleta que dependen del consumo total (transporte, potencia) se distribuyen en proporción al consumo de cada parcela.

### 3. Cuota fija
Los cargos fijos de la boleta (administración de servicio, cargo público) se dividen en partes iguales entre todas las parcelas activas.

> **El diferencial** — la diferencia entre el kWh que cobró la compañía y la suma de todos los remarcadores — también se distribuye en la cuota fija, asegurando que la suma de todas las liquidaciones **siempre cuadra con el total de la boleta.**

---

## ¿Qué ve el comunero?

Desde su celular, el comunero puede ver:

- **El monto total a pagar** ese mes
- El desglose: energía + prorrateo variable + cuota fija
- Si su pago fue **confirmado** por la administración
- El historial de períodos anteriores
- La imagen original de la boleta eléctrica

---

## Beneficios para la comunidad

| Antes | Con EnerCheck |
|-------|--------------|
| Cálculos manuales en Excel | Cálculo automático en segundos |
| Resultado enviado por WhatsApp/papel | Cada comunero lo ve en su celular |
| Sin detalle del cálculo | Desglose completo y transparente |
| Errores difíciles de corregir | Corrección en 1 clic, recálculo instantáneo |
| Sin historial accesible | Historial de todos los períodos disponible |
| Proceso toma días | Proceso completo en menos de 30 minutos |

---

## Inteligencia Artificial integrada

Al cargar la boleta, el administrador sube una **foto** del documento físico.

EnerCheck usa **Google Gemini Vision** (la misma IA que alimenta Google) para leer automáticamente:
- Total de kWh de la boleta
- Monto neto de electricidad
- Monto total con IVA
- Cada ítem de la boleta con su tipo de cargo

El administrador **revisa y confirma** antes de guardar. La IA ahorra tiempo pero el humano siempre tiene la última palabra.

---

## Seguridad y control

- Cada acción (carga de boleta, edición de lectura, cierre de período) queda **registrada** con quién la hizo y cuándo
- El período no se puede modificar una vez publicado
- Cada comunero solo ve **su propia información**
- Acceso por usuario y contraseña

---

## Tecnología

EnerCheck funciona **100% en la nube**, sin necesidad de instalar nada en los computadores del condominio.

- Accesible desde cualquier navegador (computador, tablet, celular)
- Interfaz instalable como app en iOS y Android
- Base de datos con respaldo automático

---

## Próximos pasos sugeridos

1. **Validar el primer período** — cerrar y publicar Marzo 2026 para que los comuneros puedan ver su primera liquidación
2. **Capacitar al lector** — mostrarle cómo capturar lecturas desde el celular
3. **Comunicar a los comuneros** — enviar sus credenciales de acceso
4. **Operar Abril 2026** — primer período completo operado con EnerCheck

---

*Sistema desarrollado para Condominio Santa Laura · 2026*
*Tecnología: FastAPI · React · PostgreSQL · Google Gemini Vision*
