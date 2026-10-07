#!/usr/bin/env bash
# Prueba de punta a punta de enercheck-ci (respaldo externo incremental y restauración) en Docker local,
# con un "R2" falso en una carpeta (remoto rclone de tipo local) y una llave age de prueba.
#
# Crea contenedores y volúmenes con los nombres de producción (enercheck_db, enercheck_backend,
# enercheck_uploads, enercheck_privado), marcados con la etiqueta enercheck.prueba=1, y los borra al
# terminar. Se niega a correr si ya existen sin esa etiqueta: NUNCA ejecutarlo en el servidor.
#
# Desde la raíz del repo (Git Bash en Windows: anteponer MSYS_NO_PATHCONV=1):
#   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/infra/servidor:/src:ro" \
#       ubuntu:24.04 bash /src/pruebas/probar-enercheck-ci.sh
# Con ubuntu:24.04 instala age, rclone y docker-cli en cada corrida. Para no depender del mirror, una vez:
#   printf 'FROM ubuntu:24.04\nRUN apt-get update && apt-get install -y --no-install-recommends age rclone docker-cli ca-certificates\n' \
#       | docker build -t enercheck-ci-prueba -
# y usar enercheck-ci-prueba en lugar de ubuntu:24.04.
set -euo pipefail

CI=/src/enercheck-ci
ci() { bash "$CI" "$@"; }
ETIQUETA=enercheck.prueba=1
export ENERCHECK_DIR=/srv/enercheck
export ENERCHECK_REMOTO=r2:/srv/r2
LLAVE=/srv/llave-prueba.key
SHA=0123456789abcdef0123456789abcdef01234567
fallos=0

paso() { printf '\n=== %s\n' "$*"; }
ok() { printf '  ✔ %s\n' "$*"; }
mal() { printf '  ✘ %s\n' "$*"; fallos=$((fallos + 1)); }
comprobar() {  # comprobar "<descripción>" <orden...>
    local desc=$1; shift
    if "$@"; then ok "$desc"; else mal "$desc"; fi
}
sql() { docker exec enercheck_db psql -U enercheck -d enercheck -tAq -c "$1"; }
en_volumen() { docker run --rm --network none -v enercheck_uploads:/v/uploads -v enercheck_privado:/v/privado postgres:16-alpine sh -c "$1"; }
remotos() { find /srv/r2/archivos -type f | wc -l; }

# --- Herramientas (en ubuntu:24.04) ---
if ! command -v age >/dev/null || ! command -v rclone >/dev/null || ! command -v docker >/dev/null; then
    apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq age rclone docker-cli >/dev/null 2>&1 \
        || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq age rclone docker.io >/dev/null
fi

for nombre in enercheck_db enercheck_backend; do
    if docker inspect "$nombre" >/dev/null 2>&1 \
        && [ "$(docker inspect -f '{{index .Config.Labels "enercheck.prueba"}}' "$nombre")" != 1 ]; then
        echo "Existe $nombre y no es de prueba: abortando para no tocarlo" >&2
        exit 1
    fi
done

limpiar() {
    docker rm -f enercheck_db enercheck_backend >/dev/null 2>&1 || true
    docker volume rm enercheck_uploads enercheck_privado enercheck_pgdata_prueba >/dev/null 2>&1 || true
}
trap limpiar EXIT
limpiar

levantar_db() {
    docker run -d --name enercheck_db --label "$ETIQUETA" -v enercheck_pgdata_prueba:/var/lib/postgresql/data \
        -e POSTGRES_USER=enercheck -e POSTGRES_DB=enercheck -e POSTGRES_PASSWORD=prueba postgres:16-alpine >/dev/null
    until docker exec enercheck_db pg_isready -U enercheck -d enercheck >/dev/null 2>&1; do sleep 1; done
    sleep 2
}

# --- Preparación: "servidor" con base, API falsa (siempre sana) y archivos ---
paso "Preparación"
docker volume create --label "$ETIQUETA" enercheck_uploads >/dev/null
docker volume create --label "$ETIQUETA" enercheck_privado >/dev/null
levantar_db
docker run -d --name enercheck_backend --label "$ETIQUETA" \
    -v enercheck_uploads:/app/uploads -v enercheck_privado:/app/privado \
    --health-cmd true --health-interval 2s postgres:16-alpine sleep infinity >/dev/null
sql "CREATE TABLE compras (id int primary key, voucher text); INSERT INTO compras VALUES (1, 'v1.png');"
en_volumen 'mkdir -p /v/uploads/boletas /v/uploads/condominios/1 /v/privado/vouchers \
    && echo boleta > /v/uploads/boletas/b1.jpg && echo logo > /v/uploads/condominios/1/logo-1.png \
    && echo voucher-uno > /v/privado/vouchers/v1.png && chown -R 10001:10001 /v/uploads /v/privado'

mkdir -p "$ENERCHECK_DIR" /srv/r2/diario /srv/r2/predeploy /srv/r2/archivos
age-keygen -o "$LLAVE" 2>/dev/null
age-keygen -y "$LLAVE" > "$ENERCHECK_DIR/respaldos.age.pub"
printf '[r2]\ntype = local\n' > "$ENERCHECK_DIR/rclone.conf"
ok "base, 3 archivos, llave y remoto falso listos"

# --- Respaldo ---
paso "Primer respaldo diario: sube la base y todos los archivos"
ci respaldar diario
comprobar "conjunto remoto completo (dump, imagen y .sha256)" \
    test "$(find /srv/r2/diario -name 'diario-*.dump.age' -o -name 'diario-*.imagen.txt.age' -o -name 'diario-*.sha256' | wc -l)" -eq 3
comprobar "3 archivos cifrados en el remoto" test "$(remotos)" -eq 3
comprobar "el respaldo local ya no lleva .archivos.tar.gz" test -z "$(find "$ENERCHECK_DIR/respaldos" -name '*.archivos.tar.gz')"
comprobar "nada en claro en el remoto" sh -c '! grep -rq voucher-uno /srv/r2'

paso "Segundo respaldo sin cambios: no sube archivos"
sleep 1
salida=$(ci respaldar diario)
echo "$salida"
comprobar "informa «nada nuevo»" grep -q "nada nuevo" <<< "$salida"
comprobar "siguen 3 archivos remotos" test "$(remotos)" -eq 3

paso "Archivo nuevo: sube solo ese"
en_volumen 'echo voucher-dos > /v/privado/vouchers/v2.png && chown 10001:10001 /v/privado/vouchers/v2.png'
sql "INSERT INTO compras VALUES (2, 'v2.png');"
sleep 1
salida=$(ci respaldar "$SHA")
echo "$salida"
comprobar "sube 1 archivo" grep -q "Archivos: 1 nuevos" <<< "$salida"
comprobar "conjunto predeploy con el SHA" test -n "$(find /srv/r2/predeploy -name "predeploy-*-${SHA:0:12}.sha256")"

paso "Archivo borrado en el servidor: sigue en el remoto"
en_volumen 'rm /v/uploads/condominios/1/logo-1.png'
sleep 1
ci respaldar diario >/dev/null
comprobar "el logo borrado sigue en el remoto" test -f /srv/r2/archivos/uploads/condominios/1/logo-1.png.age

paso "Descifrar a mano un voucher del remoto"
comprobar "age -d devuelve el contenido original" \
    test "$(age -d -i "$LLAVE" /srv/r2/archivos/privado/vouchers/v2.png.age)" = voucher-dos

paso "Falla del remoto: error y la copia local se conserva"
antes=$(find "$ENERCHECK_DIR/respaldos" -name '*.dump' | wc -l)
sleep 1
if env ENERCHECK_REMOTO=noexiste:/x bash "$CI" respaldar "$SHA" >/dev/null 2>&1; then
    mal "respaldar debió fallar con un remoto inválido"
else
    ok "respaldar falla (el deploy no seguiría)"
fi
comprobar "el dump local nuevo se conserva" test "$(find "$ENERCHECK_DIR/respaldos" -name '*.dump' | wc -l)" -eq $((antes + 1))

# --- Restauración: casos que NO deben tocar nada ---
sql "INSERT INTO compras VALUES (99, 'posterior');"
paso "listar"
ci listar r2
ci listar local

paso "Sin --confirmar: no hace nada"
if ci restaurar ultimo --llave "$LLAVE" >/dev/null 2>&1; then mal "debió salir con error"; else ok "sale sin restaurar"; fi
comprobar "la fila posterior sigue" test "$(sql 'SELECT count(*) FROM compras WHERE id = 99')" -eq 1

paso "Por la llave del CI (SSH): rechazado"
if env SSH_ORIGINAL_COMMAND="restaurar ultimo" bash "$CI" >/dev/null 2>&1; then mal "debió rechazarse"; else ok "rechazado"; fi

paso "Llave incorrecta: no toca nada"
age-keygen -o /srv/otra.key 2>/dev/null
if ci restaurar ultimo --llave /srv/otra.key --confirmar >/dev/null 2>&1; then mal "debió fallar"; else ok "falla"; fi
comprobar "la fila posterior sigue" test "$(sql 'SELECT count(*) FROM compras WHERE id = 99')" -eq 1

paso "Respaldo remoto alterado (no coincide su .sha256): no toca nada"
mkdir -p /srv/r2-copia && cp -a /srv/r2/diario /srv/r2-copia/
ultimo_remoto=$(find /srv/r2/diario -name '*.dump.age' | sort | tail -n 1)
echo basura >> "$ultimo_remoto"
if ci restaurar ultimo --llave "$LLAVE" --confirmar >/dev/null 2>&1; then mal "debió fallar"; else ok "falla"; fi
comprobar "la fila posterior sigue" test "$(sql 'SELECT count(*) FROM compras WHERE id = 99')" -eq 1
rm -rf /srv/r2/diario && mv /srv/r2-copia/diario /srv/r2/diario

paso "Dump local truncado: no toca nada"
cualquiera=$(find "$ENERCHECK_DIR/respaldos" -name 'diario-*.dump' | head -n 1)
head -c 200 "$cualquiera" > "$ENERCHECK_DIR/respaldos/diario-20000101-000000.dump"
if ci restaurar diario-20000101-000000 --desde local --confirmar >/dev/null 2>&1; then mal "debió fallar"; else ok "falla"; fi
comprobar "la fila posterior sigue" test "$(sql 'SELECT count(*) FROM compras WHERE id = 99')" -eq 1
comprobar "no quedó la base temporal" test "$(docker exec enercheck_db psql -U enercheck -d postgres -tAc "SELECT count(*) FROM pg_database WHERE datname = 'enercheck_restaurando'")" -eq 0
rm -f "$ENERCHECK_DIR/respaldos/diario-20000101-000000.dump"

# --- Restauración local tras un "deploy fallido" ---
paso "Restaurar local el predeploy: vuelve la base, los archivos quedan intactos"
predeploy=$(ci listar local | awk '/predeploy-/ { print $1; exit }')
ci restaurar "$predeploy" --desde local --confirmar
comprobar "la fila posterior ya no está" test "$(sql 'SELECT count(*) FROM compras WHERE id = 99')" -eq 0
comprobar "la base anterior quedó como enercheck_previa" \
    test "$(docker exec enercheck_db psql -U enercheck -d enercheck_previa -tAc 'SELECT count(*) FROM compras WHERE id = 99')" -eq 1
comprobar "API sana" test "$(docker inspect -f '{{.State.Health.Status}}' enercheck_backend)" = healthy

# --- Servidor perdido: base y volúmenes vacíos, restaurar desde el remoto ---
paso "Servidor perdido: todo vacío y restaurar desde r2"
docker rm -f enercheck_db enercheck_backend >/dev/null
docker volume rm enercheck_uploads enercheck_privado enercheck_pgdata_prueba >/dev/null
docker volume create --label "$ETIQUETA" enercheck_uploads >/dev/null
docker volume create --label "$ETIQUETA" enercheck_privado >/dev/null
levantar_db
sql "CREATE TABLE migracion_nueva (id int);"   # lo que crearía el primer deploy en el servidor nuevo
docker run -d --name enercheck_backend --label "$ETIQUETA" \
    -v enercheck_uploads:/app/uploads -v enercheck_privado:/app/privado \
    --health-cmd true --health-interval 2s postgres:16-alpine sleep infinity >/dev/null
ci restaurar ultimo --llave - --confirmar < "$LLAVE"
comprobar "vuelven las compras 1 y 2" test "$(sql 'SELECT count(*) FROM compras WHERE id IN (1, 2)')" -eq 2
comprobar "no queda la tabla del deploy vacío (la base se reemplaza entera)" \
    test "$(sql "SELECT count(*) FROM pg_tables WHERE tablename = 'migracion_nueva'")" -eq 0
comprobar "vuelven los 4 archivos (incluido el logo borrado)" test "$(en_volumen 'find /v -type f | wc -l')" -eq 4
comprobar "contenido correcto" test "$(en_volumen 'cat /v/privado/vouchers/v1.png')" = voucher-uno
comprobar "dueño 10001 en archivos y carpetas" test -z "$(en_volumen 'find /v/uploads /v/privado ! -user 10001')"
comprobar "la API puede crear carpetas nuevas (permisos)" \
    docker exec -u 10001 enercheck_backend sh -c 'mkdir -p /app/uploads/condominios/2 && touch /app/privado/vouchers/nuevo'
comprobar "API sana" test "$(docker inspect -f '{{.State.Health.Status}}' enercheck_backend)" = healthy

paso "Restaurar otra vez con los volúmenes completos: no copia archivos"
salida=$(ci restaurar ultimo --llave "$LLAVE" --confirmar)
echo "$salida"
comprobar "0 archivos que faltan" grep -q "base y 0 archivos" <<< "$salida"

echo
if [ "$fallos" -eq 0 ]; then echo "TODO OK"; else echo "FALLOS: $fallos"; exit 1; fi
