#!/bin/sh
# Arranque del backend en producción:
#   1. app.arranque: valida la configuración, espera la base, migra, carga los catálogos y el
#      super admin (sale con 1 si algo falla, y el deploy lo detecta porque el contenedor no queda sano);
#   2. uvicorn sin --reload, confiando en X-Forwarded-* solo desde dokploy-network (FORWARDED_ALLOW_IPS),
#      por donde llegan los nginx del portal y la landing.
set -e

python -m app.arranque

exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:?FORWARDED_ALLOW_IPS es obligatorio}"
