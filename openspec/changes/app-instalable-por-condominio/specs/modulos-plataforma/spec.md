# Spec Delta

## ADDED Requirements

### Requirement: App instalable con la identidad del condominio

El portal DEBE (SHALL) ofrecer un manifiesto de app (PWA) generado según el dominio por el que se accede:
- si el dominio corresponde al `portal_url` de un condominio, el nombre corto DEBE (SHALL) ser el nombre del condominio, el nombre completo "<nombre del condominio> · <nombre de la plataforma>" y el color de tema su color institucional;
- si no corresponde a ninguno, DEBE (SHALL) presentarse con la marca de la plataforma.

Los datos DEBEN (SHALL) leerse de la base en cada solicitud, de modo que un cambio en el condominio no requiera desplegar. El manifiesto DEBE (SHALL) declarar íconos existentes de 192 y 512 píxeles, incluida una versión *maskable*.

#### Scenario: Instalar desde el portal de Santa Laura

- **WHEN** un vecino instala la app desde `portal.comunidadsantalaura.cl`
- **THEN** la app se llama "Santa Laura" bajo el ícono y "Santa Laura · EFFIComunidad" como nombre completo, con el color del condominio

#### Scenario: Dominio sin condominio

- **WHEN** se accede al portal desde un dominio que no es el `portal_url` de ningún condominio
- **THEN** el manifiesto usa el nombre y el color de la plataforma

#### Scenario: Cambio de nombre del condominio

- **WHEN** el super admin cambia el nombre de un condominio
- **THEN** el manifiesto siguiente ya trae el nombre nuevo, sin desplegar

### Requirement: Marca pública del portal por dominio

El sistema DEBE (SHALL) exponer `GET /api/v1/portal/marca`, sin autenticación. Devuelve el nombre y el color del condominio del dominio, o los de la plataforma si no hay coincidencia, sin ningún otro dato del condominio. El portal DEBE (SHALL) usarla, antes de iniciar sesión, para el título de la pestaña y el nombre que iPhone propone al agregar la app a la pantalla de inicio.

#### Scenario: Pantalla de ingreso de Santa Laura

- **WHEN** alguien abre `https://portal.comunidadsantalaura.cl/login`
- **THEN** la pestaña muestra "Santa Laura · EFFIComunidad" y, al agregarla a inicio en iPhone, propone el nombre "Santa Laura"
