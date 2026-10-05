# Excepciones de seguridad

Vulnerabilidades aceptadas temporalmente en el pipeline (`.github/workflows/deploy.yml`). Cada una necesita motivo, alcance real en EnerCheck y fecha de revisión. Sin entrada aquí, no se agrega a `.trivyignore` ni a `security/pip-audit-ignore.txt`.

| ID | Dónde | Motivo | Revisar |
|----|-------|--------|---------|
| — | — | Sin excepciones vigentes | — |

## Historial

- 2026-10-02: `python-jose` se reemplazó por `PyJWT` para no depender de `ecdsa` (CVE-2024-23342, sin parche). `npm audit fix` subió `axios` y `form-data` a versiones sin avisos `high`.
