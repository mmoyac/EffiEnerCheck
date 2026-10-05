#!/usr/bin/env bash
# Instala en el servidor de producción las piezas de EnerCheck que no gestiona Dokploy (ver DEPLOY.md):
#   - /opt/enercheck/bin/enercheck-ci  (respaldos y verificación de deploy)
#   - /opt/enercheck/respaldos         (700, solo root)
#   - /etc/cron.d/enercheck-respaldo   (respaldo diario 03:30, hora del servidor = America/Santiago)
# Idempotente: se puede volver a ejecutar tras cambiar enercheck-ci.
#
#   scp infra/servidor/* comunidad:/tmp/enercheck-instalar/ && ssh comunidad 'bash /tmp/enercheck-instalar/instalar.sh'
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecutar como root" >&2; exit 1; }
ORIGEN=$(cd "$(dirname "$0")" && pwd)

install -d -m 755 /opt/enercheck /opt/enercheck/bin
install -d -m 700 /opt/enercheck/respaldos
install -m 755 "$ORIGEN/enercheck-ci" /opt/enercheck/bin/enercheck-ci

# El cron usa la hora del sistema: el servidor debe estar en hora de Chile.
if [ "$(timedatectl show -p Timezone --value)" != America/Santiago ]; then
    timedatectl set-timezone America/Santiago
    systemctl restart cron
fi

cat > /etc/cron.d/enercheck-respaldo <<'EOF'
# Respaldo diario de EnerCheck (base + archivos), conserva 14. Lo instala infra/servidor/instalar.sh.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 3 * * * root /opt/enercheck/bin/enercheck-ci respaldar diario >> /var/log/enercheck-respaldo.log 2>&1
EOF
chmod 644 /etc/cron.d/enercheck-respaldo

echo "Instalado. Hora del servidor: $(date)"
echo
echo "Falta (una sola vez): la llave del CI en /root/.ssh/authorized_keys, con comando forzado:"
echo '  command="/opt/enercheck/bin/enercheck-ci",restrict ssh-ed25519 AAAA... enercheck-ci@github-actions'
