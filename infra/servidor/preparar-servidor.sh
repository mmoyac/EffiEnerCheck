#!/usr/bin/env bash
# Deja un Ubuntu 24.04 recién creado listo para producción de EnerCheck (ver DEPLOY.md §2 y el runbook
# «Migrar o recuperar el VPS»). Idempotente: cada fase se puede volver a ejecutar.
#
#   [PC] scp -r infra/servidor/* <vps>:/tmp/enercheck-instalar/
#   [VPS] bash /tmp/enercheck-instalar/preparar-servidor.sh <fase> [opciones]
#
# Fases, en este orden:
#   sistema        paquetes, SSH solo con llaves, ufw (22 limitado, 80, 443), fail2ban, hora de Chile,
#                  actualizaciones de seguridad automáticas
#   dokploy        Docker y Dokploy (versiones fijadas), con el panel :3000 abierto SOLO para la IP de
#                  esta sesión SSH (o la de --ip <IPv4>); verifica la subred de dokploy-network. En un
#                  servidor que ya tiene Dokploy no instala nada (el instalador desarma el swarm): solo verifica.
#   cerrar-panel   después de crear el administrador y el dominio del panel en Dokploy: cierra :3000
#   aplicacion     enercheck-ci, cron del respaldo diario, llave pública age, token de R2 (pedido por
#                  teclado, nunca como argumento) y llave del CI con comando forzado
#                  opciones: --llave-ci "ssh-ed25519 AAAA... enercheck-ci@github-actions"
#                            --reemplazar-token   (vuelve a pedir el token de R2)
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecutar como root" >&2; exit 1; }
ORIGEN=$(cd "$(dirname "$0")" && pwd)
BASE=/opt/enercheck

# Versiones del servidor de referencia (2026-10). Se suben a propósito, probando antes en un simulacro.
DOCKER_VERSION=${DOCKER_VERSION:-28.5.0}
DOKPLOY_VERSION=${DOKPLOY_VERSION:-v0.30.8}
# rclone oficial y no el de Ubuntu (1.60): tras cada subida, el 1.60 consulta ?versionId=, que R2 no
# implementa (501), y cada subida falla en su primer intento. Checksums de downloads.rclone.org/v1.75.1/SHA256SUMS.
RCLONE_VERSION=v1.75.1
declare -A RCLONE_SHA256=(
    [amd64]=09c9f7606ed9e31eecc1eec26a89992cf2931a8d2d1a5f0ae2bb1c11630ffb15
    [arm64]=773f3a76615f91f7d4654183a537afddce3343c8d99ac1d74984f060f2ade2d9
)
# Subred en la que confían frontend/ y landing/nginx.prod.conf (set_real_ip_from) y FORWARDED_ALLOW_IPS.
SUBRED_DOKPLOY=10.0.1.0/24
BUCKET=efficomunidad-respaldos

uso() {
    sed -n '8,19p' "$0" >&2
    exit 2
}

titulo() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------------------------------------------
instalar_rclone() {
    local arq deb
    if [ "$(rclone version 2>/dev/null | awk 'NR == 1 { print $2 }')" = "$RCLONE_VERSION" ]; then
        echo "rclone $RCLONE_VERSION ya instalado"
        return 0
    fi
    arq=$(dpkg --print-architecture)
    [ -n "${RCLONE_SHA256[$arq]:-}" ] || { echo "Arquitectura sin checksum de rclone: $arq" >&2; exit 1; }
    deb=/tmp/rclone-$RCLONE_VERSION-linux-$arq.deb
    curl -fsSL -o "$deb" "https://downloads.rclone.org/$RCLONE_VERSION/rclone-$RCLONE_VERSION-linux-$arq.deb"
    echo "${RCLONE_SHA256[$arq]}  $deb" | sha256sum -c --quiet || { rm -f "$deb"; echo "Checksum de rclone inválido" >&2; exit 1; }
    dpkg -i "$deb" >/dev/null
    rm -f "$deb"
    echo "rclone $(rclone version | awk 'NR == 1 { print $2 }') instalado"
}

fase_sistema() {
    titulo "Paquetes"
    apt-get update -q
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
        ufw fail2ban age unattended-upgrades ca-certificates curl
    instalar_rclone
    cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

    titulo "SSH solo con llaves"
    # Sin una llave autorizada, desactivar las contraseñas dejaría el servidor inaccesible.
    if [ ! -s /root/.ssh/authorized_keys ] && ! grep -qs '^ssh-' /home/*/.ssh/authorized_keys; then
        echo "No hay ninguna llave SSH autorizada: agrega la tuya antes (ssh-copy-id) o te quedarás fuera" >&2
        exit 1
    fi
    cat > /etc/ssh/sshd_config.d/00-endurecer.conf <<'EOF'
# Endurecimiento: solo llaves (gana sobre otros archivos por orden alfabético)
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
EOF
    sshd -t
    systemctl reload ssh

    titulo "Firewall"
    ufw default deny incoming
    ufw default allow outgoing
    ufw limit 22/tcp comment 'SSH (con limite de intentos)'
    ufw allow 80/tcp comment 'HTTP Traefik'
    ufw allow 443/tcp comment 'HTTPS Traefik'
    ufw allow 443/udp comment 'HTTP/3 Traefik'
    ufw --force enable

    titulo "fail2ban"
    # Ubuntu 24.04 registra SSH como ssh.service (no sshd.service): sin journalmatch no banea nada.
    cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[DEFAULT]
backend = systemd
banaction = ufw
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled  = true
maxretry = 5
findtime = 10m
bantime  = 1h
bantime.increment = true
bantime.maxtime = 1w
journalmatch = _SYSTEMD_UNIT=ssh.service + _COMM=sshd
mode = aggressive
EOF
    # reload y no restart: un restart levanta los baneos vigentes.
    if systemctl is-active --quiet fail2ban; then
        systemctl reload fail2ban
    else
        systemctl enable --now fail2ban
    fi

    titulo "Hora"
    # El cron del respaldo usa la hora del sistema: el servidor debe estar en hora de Chile.
    if [ "$(timedatectl show -p Timezone --value)" != America/Santiago ]; then
        timedatectl set-timezone America/Santiago
        systemctl restart cron
    fi
    echo "Sistema listo. Hora del servidor: $(date)"
}

# ---------------------------------------------------------------------------------------------------
verificar_subred() {
    local subred
    subred=$(docker network inspect dokploy-network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || true)
    if [ "$subred" != "$SUBRED_DOKPLOY" ]; then
        cat >&2 <<EOF
dokploy-network tiene la subred «${subred:-ausente}» y las imágenes confían en $SUBRED_DOKPLOY
(set_real_ip_from de frontend/ y landing/nginx.prod.conf, y FORWARDED_ALLOW_IPS). Con otra subred, el
límite de intentos de inicio de sesión vería la IP del proxy y no la del visitante.
En un servidor nuevo: reinstala Dokploy en un swarm limpio (la primera red overlay después de ingress
toma $SUBRED_DOKPLOY). No sigas con el deploy hasta que coincida.
EOF
        exit 1
    fi
    echo "dokploy-network: $subred ✔"
}

# El puerto 3000 lo publica Docker, que no pasa por ufw: se filtra en la cadena DOCKER-USER.
abrir_panel_solo_para() {
    local ip=$1
    iptables -C DOCKER-USER -p tcp --dport 3000 ! -s "$ip" -j DROP 2>/dev/null \
        || iptables -I DOCKER-USER -p tcp --dport 3000 ! -s "$ip" -j DROP
    if ip6tables -L DOCKER-USER >/dev/null 2>&1; then
        ip6tables -C DOCKER-USER -p tcp --dport 3000 -j DROP 2>/dev/null \
            || ip6tables -I DOCKER-USER -p tcp --dport 3000 -j DROP
    fi
}

fase_dokploy() {
    if docker service inspect dokploy >/dev/null 2>&1; then
        echo "Dokploy ya está instalado: no se reinstala (el instalador desarma el swarm)."
        verificar_subred
        return 0
    fi

    local ip_operador=${1:-}
    [ -n "$ip_operador" ] || ip_operador=${SSH_CLIENT:-}
    ip_operador=${ip_operador%% *}
    if [[ ! "$ip_operador" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        echo "No se pudo saber tu IP (el panel se abre solo para ella). Indícala: dokploy --ip <tu IP pública>" >&2
        exit 1
    fi

    titulo "Docker $DOCKER_VERSION"
    if ! command -v docker >/dev/null; then
        curl -fsSL https://get.docker.com | sh -s -- --version "$DOCKER_VERSION"
        apt-mark hold docker-ce docker-ce-cli docker-ce-rootless-extras
    fi
    systemctl enable --now docker
    # Antes de que exista el panel: mientras no haya administrador, quien llegue primero lo crea.
    abrir_panel_solo_para "$ip_operador"
    echo "Panel :3000 solo para $ip_operador"

    titulo "Dokploy $DOKPLOY_VERSION"
    curl -fsSL https://dokploy.com/install.sh -o /tmp/dokploy-install.sh
    DOKPLOY_VERSION=$DOKPLOY_VERSION bash /tmp/dokploy-install.sh
    rm -f /tmp/dokploy-install.sh
    abrir_panel_solo_para "$ip_operador"   # por si el instalador reinició Docker
    verificar_subred

    local ip_publica
    ip_publica=$(curl -fsS4 --max-time 5 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    cat <<EOF

Ahora, sin demora, desde tu navegador (solo tu IP $ip_operador puede entrar):
  1. http://$ip_publica:3000  → crea la cuenta de administrador de Dokploy.
  2. Settings → Web Server: dominio del panel (p. ej. dokploy.<dominio>) con HTTPS; en Cloudflare, el
     registro A de ese dominio → $ip_publica (Solo DNS).
  3. Cuando el panel responda por https://dokploy.<dominio>:
       bash $0 cerrar-panel
EOF
}

fase_cerrar_panel() {
    docker service inspect dokploy >/dev/null 2>&1 || { echo "Dokploy no está instalado" >&2; exit 1; }
    if docker service inspect dokploy --format '{{json .Endpoint.Spec.Ports}}' | grep -q '"PublishedPort":3000'; then
        docker service update --publish-rm published=3000,target=3000,mode=host dokploy >/dev/null
        echo "Puerto 3000 del panel cerrado (desde ahora, solo por su dominio con HTTPS)"
    else
        echo "El puerto 3000 ya estaba cerrado"
    fi
    # Quita las reglas temporales de :3000 que abrió la fase dokploy
    iptables -S DOCKER-USER 2>/dev/null | grep -- '--dport 3000' | sed 's/^-A /-D /' \
        | while read -r regla; do read -r -a partes <<< "$regla"; iptables "${partes[@]}"; done
    ip6tables -S DOCKER-USER 2>/dev/null | grep -- '--dport 3000' | sed 's/^-A /-D /' \
        | while read -r regla; do read -r -a partes <<< "$regla"; ip6tables "${partes[@]}"; done
    verificar_subred
}

# ---------------------------------------------------------------------------------------------------
configurar_token_r2() {
    local id secreto endpoint
    echo "Token de R2 del servidor (Cloudflare → R2 → Administrar tokens de API; permiso «Lectura y"
    echo "escritura de objetos» solo en $BUCKET). Se guarda en $BASE/rclone.conf (600)."
    echo "Pega cada dato y presiona Enter. Si uno no tiene el formato esperado, se vuelve a pedir."
    # Al pegar suelen colarse espacios o retornos de carro: se quitan.
    while :; do
        read -r -p "  ID de clave de acceso (32 caracteres): " id
        id=$(tr -d '[:space:]' <<< "$id")
        [[ "$id" =~ ^[0-9a-f]{32}$ ]] && { echo "    ✔ ${#id} caracteres"; break; }
        echo "    ✘ llegaron ${#id} caracteres; debe tener 32 de 0-9 y a-f"
    done
    while :; do
        read -r -s -p "  Clave de acceso secreta (64 caracteres; al pegarla no se ve, es normal): " secreto; echo
        secreto=$(tr -d '[:space:]' <<< "$secreto")
        [[ "$secreto" =~ ^[0-9a-f]{64}$ ]] && { echo "    ✔ ${#secreto} caracteres"; break; }
        echo "    ✘ llegaron ${#secreto} caracteres; debe tener 64 de 0-9 y a-f (no es el «Valor del token»)"
    done
    while :; do
        read -r -p "  Endpoint S3 (https://<cuenta>.r2.cloudflarestorage.com): " endpoint
        endpoint=$(tr -d '[:space:]' <<< "$endpoint")
        endpoint=${endpoint%/}
        endpoint=${endpoint%/"$BUCKET"}
        [[ "$endpoint" =~ ^https://[a-z0-9]+\.r2\.cloudflarestorage\.com$ ]] && { echo "    ✔"; break; }
        echo "    ✘ formato inválido"
    done
    (
        umask 077
        cat > "$BASE/rclone.conf.nuevo" <<EOF
[r2]
type = s3
provider = Cloudflare
access_key_id = $id
secret_access_key = $secreto
endpoint = $endpoint
acl = private
no_check_bucket = true
EOF
    )
    if ! RCLONE_CONFIG="$BASE/rclone.conf.nuevo" rclone lsf "r2:$BUCKET" --max-depth 1 >/dev/null; then
        rm -f "$BASE/rclone.conf.nuevo"
        echo "El token no permite listar el bucket $BUCKET: revisa los datos" >&2
        exit 1
    fi
    mv "$BASE/rclone.conf.nuevo" "$BASE/rclone.conf"
    echo "Token de R2 verificado ✔"
}

fase_aplicacion() {
    local llave_ci='' reemplazar_token=no
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --llave-ci)         [ "$#" -ge 2 ] || uso; llave_ci=$2; shift 2 ;;
            --reemplazar-token) reemplazar_token=si; shift ;;
            *)                  uso ;;
        esac
    done
    if ! command -v age >/dev/null || ! command -v rclone >/dev/null; then
        echo "Faltan age o rclone: ejecuta antes la fase sistema" >&2
        exit 1
    fi

    titulo "enercheck-ci"
    install -d -m 755 "$BASE" "$BASE/bin"
    install -d -m 700 "$BASE/respaldos"
    install -m 755 "$ORIGEN/enercheck-ci" "$BASE/bin/enercheck-ci"
    install -m 644 "$ORIGEN/respaldos.age.pub" "$BASE/respaldos.age.pub"
    echo "Llave pública de respaldos: $(cat "$BASE/respaldos.age.pub")"

    cat > /etc/cron.d/enercheck-respaldo <<'EOF'
# Respaldo diario de EnerCheck (base + archivos nuevos, local y cifrado en R2). Lo instala infra/servidor/preparar-servidor.sh.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 3 * * * root /opt/enercheck/bin/enercheck-ci respaldar diario >> /var/log/enercheck-respaldo.log 2>&1
EOF
    chmod 644 /etc/cron.d/enercheck-respaldo

    titulo "Token de R2"
    if [ -s "$BASE/rclone.conf" ] && [ "$reemplazar_token" = no ]; then
        echo "Ya configurado ($BASE/rclone.conf). Para cambiarlo: --reemplazar-token"
    else
        configurar_token_r2
    fi
    chmod 600 "$BASE/rclone.conf"

    titulo "Llave del CI"
    if [ -n "$llave_ci" ]; then
        [[ "$llave_ci" =~ ^ssh-ed25519\ [A-Za-z0-9+/=]+( .*)?$ ]] || { echo "Llave del CI inválida (se espera ssh-ed25519 ...)" >&2; exit 1; }
        local cuerpo
        cuerpo=$(awk '{print $2}' <<< "$llave_ci")
        install -d -m 700 /root/.ssh
        touch /root/.ssh/authorized_keys
        chmod 600 /root/.ssh/authorized_keys
        if grep -qF "$cuerpo" /root/.ssh/authorized_keys; then
            echo "La llave del CI ya está autorizada"
        else
            echo "command=\"$BASE/bin/enercheck-ci\",restrict $llave_ci" >> /root/.ssh/authorized_keys
            echo "Llave del CI agregada con comando forzado"
        fi
    elif grep -q "command=\"$BASE/bin/enercheck-ci\"" /root/.ssh/authorized_keys 2>/dev/null; then
        echo "La llave del CI ya está autorizada"
    else
        echo "AVISO: falta la llave del CI. Vuelve a ejecutar con --llave-ci \"ssh-ed25519 AAAA... enercheck-ci@github-actions\""
    fi

    echo
    echo "Aplicación lista. Hora del servidor: $(date)"
}

[ "$#" -ge 1 ] || uso
fase=$1; shift
case "$fase" in
    sistema)      [ "$#" -eq 0 ] || uso; fase_sistema ;;
    dokploy)
        case "$#" in
            0) fase_dokploy ;;
            2) [ "$1" = --ip ] || uso; fase_dokploy "$2" ;;
            *) uso ;;
        esac
        ;;
    cerrar-panel) [ "$#" -eq 0 ] || uso; fase_cerrar_panel ;;
    aplicacion)   fase_aplicacion "$@" ;;
    *)            uso ;;
esac
