# Spec Delta

## ADDED Requirements

### Requirement: Imágenes de producción construidas fuera del servidor

Las imágenes de producción DEBEN (SHALL) construirse, auditarse y publicarse en el registro desde el pipeline de integración continua. El servidor de producción NO DEBE (SHALL NOT) construir imágenes ni tener acceso al código fuente: solo descarga imágenes ya publicadas y etiquetadas con el commit que las originó.

#### Scenario: Despliegue de un commit aprobado

- **WHEN** un commit llega a la rama de producción, supera los chequeos y recibe la aprobación manual del entorno de producción
- **THEN** el pipeline publica las imágenes del backend, del portal y de la landing con la etiqueta del commit, y el servidor ejecuta exactamente esas imágenes

#### Scenario: Chequeo fallido

- **WHEN** fallan las pruebas, una auditoría de dependencias o el escaneo de vulnerabilidades críticas de una imagen
- **THEN** no se publica ninguna imagen y el servidor sigue ejecutando la versión anterior

#### Scenario: Volver a una versión anterior

- **WHEN** el operador indica la etiqueta de un commit anterior ya publicado
- **THEN** el servidor vuelve a esas imágenes sin construir nada

### Requirement: Respaldo previo a cada despliegue

Antes de cambiar las imágenes en ejecución, el despliegue DEBE (SHALL) respaldar la base de datos, los archivos subidos (públicos y privados) y la definición de servicios vigente, conservando al menos los diez respaldos más recientes. Si el respaldo falla, el despliegue NO DEBE (SHALL NOT) continuar.

#### Scenario: Respaldo exitoso

- **WHEN** se inicia un despliegue con la base en ejecución
- **THEN** se genera un respaldo identificado con la fecha y el commit, y recién entonces se cambian las imágenes

#### Scenario: Falla del respaldo

- **WHEN** el volcado de la base o de los archivos falla o queda vacío
- **THEN** el despliegue se detiene con error y la versión en ejecución no cambia

#### Scenario: Primer despliegue

- **WHEN** aún no existe la base de producción
- **THEN** el despliegue continúa sin respaldo previo

### Requirement: Despliegue verificado por salud

Un despliegue DEBE (SHALL) darse por exitoso solo cuando la API ejecuta la imagen del commit desplegado y supera su verificación de salud dentro de un plazo acotado. En caso contrario, el pipeline DEBE (SHALL) terminar con error y mostrar las últimas líneas del registro de la API.

#### Scenario: API sana

- **WHEN** tras el despliegue la API arranca con la imagen del commit, aplica las migraciones y responde sana
- **THEN** el pipeline termina con éxito

#### Scenario: API que no arranca

- **WHEN** la API no queda sana dentro del plazo, por ejemplo porque una migración falla o falta un secreto
- **THEN** el pipeline termina con error y muestra el registro de la API

### Requirement: Respaldo diario

El servidor de producción DEBE (SHALL) respaldar cada día la base de datos y los archivos subidos, conservando los respaldos de los últimos catorce días, con permisos accesibles solo para el administrador del servidor.

#### Scenario: Ejecución diaria

- **WHEN** se cumple la hora programada
- **THEN** se genera el respaldo del día y se eliminan los de más de catorce días

### Requirement: Entrada pública por dominio con TLS automático

En producción, los servicios web DEBEN (SHALL) recibir tráfico solo a través del proxy de entrada de la plataforma de despliegue, por HTTPS con certificados renovados automáticamente, y HTTP DEBE (SHALL) redirigir a HTTPS. Ningún servicio de la aplicación DEBE (SHALL) publicar puertos en el servidor, y la base de datos NO DEBE (SHALL NOT) tener salida a internet.

#### Scenario: Acceso por HTTP

- **WHEN** un visitante entra por HTTP a un dominio de la plataforma
- **THEN** es redirigido a la misma dirección por HTTPS

#### Scenario: Acceso directo a un servicio interno

- **WHEN** alguien intenta conectarse desde internet a la base de datos o a la API por un puerto del servidor
- **THEN** la conexión no es posible

### Requirement: Rutas expuestas por cada aplicación web

Cada aplicación web de producción DEBE (SHALL) limitar por sí misma las rutas de la API que expone y aplicar sus encabezados de seguridad (HSTS, `nosniff`, prohibición de marcos, política de referer y de permisos) sin depender de un proxy externo al repositorio.

- El **portal** DEBE (SHALL) exponer `/api/` y `/uploads/` y limitar la frecuencia de intentos de inicio de sesión por dirección IP del cliente.
- La **landing** DEBE (SHALL) exponer solo `GET /api/v1/sitio` y `GET /uploads/condominios/`, responder 404 a cualquier otra ruta de la API o de archivos y aplicar una política de seguridad de contenido que solo admite recursos del mismo origen.

#### Scenario: Landing pide otra ruta de la API

- **WHEN** se solicita `/api/v1/boletas/` o `/uploads/boletas/...` en el dominio de la landing
- **THEN** la respuesta es 404, sin llegar a la API

#### Scenario: Ráfaga de intentos de inicio de sesión

- **WHEN** una misma dirección IP envía muchos intentos de inicio de sesión al portal en pocos segundos
- **THEN** los intentos que exceden el límite reciben 429 sin llegar a la API

#### Scenario: Dirección del cliente

- **WHEN** una petición atraviesa el proxy de entrada y el servidor web de la aplicación
- **THEN** la API y el límite de intentos ven la dirección IP real del visitante, no la de los proxies

#### Scenario: Variante www de la landing

- **WHEN** un visitante entra a la landing por `www.<dominio>`
- **THEN** es redirigido al dominio sin `www`

### Requirement: Carga inicial de producción sin datos de prueba

La carga inicial de un condominio en producción DEBE (SHALL) incluir solo su configuración (módulos, color, URL del portal y dominios de la landing), sus parcelas y sus residentes con sus asignaciones a parcelas. NO DEBE (SHALL NOT) incluir datos operativos (boletas, lecturas, liquidaciones, rifas, auditoría), cuentas de prueba ni cuentas con la clave pública de los datos de prueba. Todos los residentes cargados DEBEN (SHALL) recibir una clave inicial ingresada por el operador en el momento de la carga. La carga DEBE (SHALL) ser idempotente.

#### Scenario: Carga sobre una base nueva

- **WHEN** el operador carga Santa Laura en la base de producción recién creada
- **THEN** quedan el condominio con su configuración, sus parcelas y sus residentes asignados, y ningún período, rifa ni cuenta de prueba

#### Scenario: Repetir la carga

- **WHEN** la carga se ejecuta por segunda vez
- **THEN** no duplica registros ni cambia las claves de las cuentas que ya existen

#### Scenario: Clave inicial débil

- **WHEN** el operador ingresa una clave corta o la clave pública de los datos de prueba
- **THEN** la carga se rechaza sin escribir nada
