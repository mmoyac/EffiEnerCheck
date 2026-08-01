# gestion-parcelas Specification

## Purpose

Mantener el padrón de parcelas de cada condominio. La parcela es la unidad sobre la que se toma la lectura del remarcador y sobre la que se emite la liquidación mensual. El indicador `activa` determina qué parcelas participan del prorrateo: solo las activas reciben cuota fija y liquidación.

## Requirements

### Requirement: Alta de parcela

El sistema DEBE (SHALL) exponer `POST /api/v1/parcelas/`, restringido a roles administrativos, que crea una parcela con número identificador, nombre de propietario opcional y estado activo.

#### Scenario: Administrador de condominio crea una parcela

- **WHEN** un `admin_condominio` crea una parcela
- **THEN** el sistema la asigna automáticamente a su propio condominio, responde `201` y registra la acción `CREATE_PARCELA` en auditoría

#### Scenario: Super admin sin condominio indicado

- **WHEN** un `super_admin` crea una parcela sin especificar `condominio_id`
- **THEN** el sistema responde `400` con el detalle `"Debe especificar condominio_id"`

### Requirement: Listado de parcelas en orden natural

El sistema DEBE (SHALL) exponer `GET /api/v1/parcelas/` para cualquier rol autenticado, devolviendo las parcelas del tenant activo ordenadas por el valor numérico contenido en `numero_parcela` y, como desempate, por el texto completo del número.

#### Scenario: Orden numérico y no alfabético

- **WHEN** un condominio tiene las parcelas `"2"`, `"10"` y `"1"`
- **THEN** el sistema las devuelve en el orden `"1"`, `"2"`, `"10"` y no en orden alfabético

#### Scenario: Número de parcela sin dígitos

- **WHEN** una parcela tiene un `numero_parcela` que no contiene dígitos
- **THEN** el sistema la trata como valor numérico cero para el ordenamiento y no falla la consulta

#### Scenario: Parcelero lista parcelas

- **WHEN** un `parcelero` lista parcelas
- **THEN** el sistema devuelve únicamente las parcelas vinculadas a su usuario

### Requirement: Consulta de una parcela

El sistema DEBE (SHALL) exponer `GET /api/v1/parcelas/{parcela_id}` para cualquier rol autenticado, validando la pertenencia al tenant y, para el rol `parcelero`, la pertenencia al usuario.

#### Scenario: Parcela inexistente

- **WHEN** se solicita un identificador que no existe
- **THEN** el sistema responde `404` con el detalle `"Parcela no encontrada"`

#### Scenario: Parcelero consulta una parcela ajena

- **WHEN** un `parcelero` solicita una parcela de su condominio que no está asociada a su usuario
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a esta parcela"`

### Requirement: Modificación de parcela

El sistema DEBE (SHALL) exponer `PATCH /api/v1/parcelas/{parcela_id}`, restringido a roles administrativos, que aplica actualizaciones parciales y registra el estado previo y posterior en auditoría.

#### Scenario: Cambio de propietario

- **WHEN** un administrador actualiza el campo `propietario_nombre`
- **THEN** el sistema aplica el cambio y registra la acción `UPDATE_PARCELA` con los valores anterior y nuevo

#### Scenario: Desactivación de una parcela

- **WHEN** un administrador marca `activa` en falso
- **THEN** la parcela deja de recibir liquidaciones en los cálculos posteriores y deja de aparecer en la lista de captura del lector
