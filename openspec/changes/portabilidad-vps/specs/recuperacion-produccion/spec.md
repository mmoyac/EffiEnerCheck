# Spec Delta

## Purpose

Permitir que producción vuelva a estar operativa en un servidor nuevo, de cualquier proveedor, en alrededor de una hora y sin perder más que lo escrito desde el último respaldo, tanto si el servidor anterior dejó de existir como si se decidió migrar.

## ADDED Requirements

### Requirement: Respaldo externo cifrado

Cada respaldo de producción (el diario y el previo a un despliegue) DEBE (SHALL) copiarse a un almacenamiento de objetos externo al proveedor del servidor, cifrado antes de salir del servidor. La base de datos DEBE (SHALL) copiarse completa en cada respaldo. Los archivos subidos (públicos y privados) DEBEN (SHALL) copiarse de forma incremental: cada respaldo sube solo los archivos que aún no están en el almacenamiento externo, y un archivo borrado en el servidor NO DEBE (SHALL NOT) borrarse del almacenamiento externo. Cada respaldo de la base DEBE (SHALL) subirse después de los archivos que existían en ese momento, de modo que todo archivo al que apunte la base respaldada esté en el almacenamiento externo. La llave capaz de descifrarlos NO DEBE (SHALL NOT) estar en el servidor. Las credenciales que usa el servidor NO DEBEN (SHALL NOT) permitir borrar ni sobrescribir respaldos ya subidos.

#### Scenario: Respaldo diario subido

- **WHEN** se ejecuta el respaldo diario con el almacenamiento externo disponible
- **THEN** la base del día, la definición de servicios y la imagen en ejecución quedan en el almacenamiento externo, cifradas y con el mismo nombre que su copia local, junto con los archivos subidos desde el respaldo anterior

#### Scenario: Solo se suben archivos nuevos

- **WHEN** desde el respaldo anterior se subieron al sistema tres vouchers y ninguna otra imagen
- **THEN** el respaldo sube al almacenamiento externo solo esos tres archivos, además de la base

#### Scenario: Archivo borrado en el servidor

- **WHEN** se elimina una rifa y con ella sus vouchers del disco del servidor
- **THEN** las copias cifradas de esos vouchers permanecen en el almacenamiento externo

#### Scenario: Falla la subida antes de un despliegue

- **WHEN** el respaldo previo a un despliegue no logra subirse al almacenamiento externo
- **THEN** el despliegue se detiene con error y la versión en ejecución no cambia

#### Scenario: Falla la subida del respaldo diario

- **WHEN** el respaldo diario no logra subirse al almacenamiento externo
- **THEN** la copia local se conserva, el error queda en el registro del respaldo y el siguiente respaldo diario vuelve a intentarlo

#### Scenario: Servidor comprometido

- **WHEN** alguien con acceso total al servidor intenta leer o borrar los respaldos externos
- **THEN** no puede descifrarlos ni borrarlos con las credenciales que encuentra en el servidor

#### Scenario: Retención externa

- **WHEN** un respaldo externo de la base supera la antigüedad definida para su tipo (al menos 30 días para los diarios)
- **THEN** el almacenamiento lo elimina por su cuenta, sin intervención del servidor, y conserva los archivos subidos

### Requirement: Restauración desde un respaldo

El operador DEBE (SHALL) poder restaurar con una sola orden en el servidor el respaldo más reciente o uno elegido, tomado del almacenamiento externo o del disco local. La restauración desde el almacenamiento externo DEBE (SHALL) reponer la base de datos y todos los archivos subidos que falten en el servidor, sin borrar ni reemplazar los que ya están; la restauración local DEBE (SHALL) reponer la base y dejar los archivos como están. En ambos casos la API DEBE (SHALL) estar detenida mientras se escribe la base, y la restauración DEBE (SHALL) terminar con la API en ejecución y sana. NO DEBE (SHALL NOT) ejecutarse sin una confirmación explícita, porque reemplaza los datos vigentes.

#### Scenario: Restaurar el último respaldo externo en un servidor nuevo

- **WHEN** en un servidor recién preparado, con la aplicación desplegada y la base vacía, el operador restaura el último respaldo externo entregando la llave de descifrado
- **THEN** la base y los archivos quedan como en ese respaldo, la API arranca sana y los usuarios pueden iniciar sesión con sus claves de siempre

#### Scenario: Restaurar un respaldo local tras un despliegue fallido

- **WHEN** el operador restaura un respaldo previo a un despliegue que está en el disco del servidor
- **THEN** la base vuelve a ese momento sin necesidad del almacenamiento externo y los archivos del servidor quedan intactos

#### Scenario: Respaldo dañado o llave incorrecta

- **WHEN** el respaldo no se puede descifrar o el volcado de la base está incompleto
- **THEN** la restauración se detiene antes de tocar la base o los archivos vigentes e informa el motivo

#### Scenario: Sin confirmación

- **WHEN** el operador ejecuta la restauración sin confirmar explícitamente
- **THEN** no se modifica nada

### Requirement: Secretos de producción recuperables

La configuración secreta de producción (contraseña de la base, clave de firma de sesiones y claves de servicios externos) DEBE (SHALL) viajar en cada respaldo externo, cifrada y descifrable con la misma llave que los respaldos, sin pasos manuales del operador. Ningún secreto DEBE (SHALL) guardarse sin cifrar en el repositorio ni aparecer en los registros del pipeline.

#### Scenario: Servidor nuevo con los secretos de siempre

- **WHEN** el operador prepara un servidor nuevo y descifra la copia de los secretos
- **THEN** la aplicación arranca con la misma clave de firma y las mismas claves de servicios externos, de modo que con la base restaurada todo funciona sin reconfigurar ni generar secretos nuevos

#### Scenario: Secreto cambiado

- **WHEN** el operador cambia un secreto de producción en la plataforma de despliegue
- **THEN** el siguiente respaldo externo contiene la configuración con el valor nuevo

### Requirement: Servidor reproducible

Un servidor recién creado con la distribución soportada DEBE (SHALL) quedar listo para recibir la aplicación ejecutando un único procedimiento automatizado e idempotente, sin pasos manuales en interfaces gráficas salvo la creación del administrador y del dominio del panel de la plataforma de despliegue. Mientras el panel no tenga administrador, NO DEBE (SHALL NOT) ser accesible desde otra dirección que la del operador. El servidor resultante DEBE (SHALL) aceptar SSH solo con llaves, exponer solo los puertos de SSH, HTTP y HTTPS, quedar en la zona horaria de Chile y tener programado el respaldo diario. La red compartida con el proxy de entrada DEBE (SHALL) tener la subred en la que confían las aplicaciones web para identificar la IP real del visitante.

#### Scenario: Ubuntu recién creado

- **WHEN** el operador ejecuta el procedimiento en un servidor nuevo con la llave SSH del operador ya autorizada
- **THEN** el servidor queda endurecido, con la plataforma de despliegue instalada, las herramientas de respaldo y restauración, el respaldo diario programado y la llave del pipeline con su comando forzado

#### Scenario: Panel recién instalado

- **WHEN** la plataforma de despliegue acaba de instalarse y todavía no tiene administrador
- **THEN** su panel responde solo a la dirección IP del operador, y queda cerrado al acceso directo una vez configurado su dominio con HTTPS

#### Scenario: Volver a ejecutar

- **WHEN** el procedimiento se ejecuta sobre un servidor ya preparado
- **THEN** no duplica configuraciones ni rompe lo existente, y no reinstala la plataforma de despliegue

#### Scenario: Subred distinta a la esperada

- **WHEN** la red compartida con el proxy ya existe con una subred distinta de la configurada en las aplicaciones web
- **THEN** el procedimiento se detiene con un mensaje claro en vez de dejar un servidor en el que el límite de intentos de inicio de sesión vería la IP del proxy

### Requirement: Dominios versionados con la aplicación

Los dominios públicos del portal y de la landing, y su certificado TLS automático, DEBEN (SHALL) declararse en la definición de servicios versionada en el repositorio, de modo que un despliegue en un servidor nuevo los publique sin configurarlos a mano en la plataforma de despliegue.

#### Scenario: Primer despliegue en un servidor nuevo

- **WHEN** el pipeline despliega en un servidor recién preparado y el DNS ya apunta a él
- **THEN** el portal y la landing responden por HTTPS en sus dominios con certificados válidos, sin pasos manuales de dominios

### Requirement: Procedimiento de migración y recuperación probado

El repositorio DEBE (SHALL) documentar un procedimiento paso a paso para migrar producción a otro servidor y para recuperarla cuando el servidor dejó de existir, indicando dónde se ejecuta cada paso y cómo verificar el resultado. El procedimiento DEBE (SHALL) haberse ejecutado completo al menos una vez en un servidor desechable, registrando la fecha y el tiempo total, y NO DEBE (SHALL NOT) darse por vigente si un cambio de infraestructura posterior no se reflejó en él.

#### Scenario: Migración planificada

- **WHEN** el operador decide cambiar de proveedor
- **THEN** sigue el procedimiento, la ventana sin servicio se limita al tiempo entre el último respaldo y el cambio de DNS, y no se pierde ninguna escritura

#### Scenario: Servidor perdido

- **WHEN** el servidor de producción deja de existir sin aviso
- **THEN** el operador vuelve a tener producción en un servidor nuevo en alrededor de una hora, perdiendo solo lo escrito después del último respaldo externo

#### Scenario: Simulacro

- **WHEN** se ejecuta el simulacro en un servidor desechable con un dominio de prueba
- **THEN** la aplicación queda operativa con los datos del último respaldo externo, se registra el tiempo total y el servidor se destruye al terminar
