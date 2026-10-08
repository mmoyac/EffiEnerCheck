# Tasks

## 1. Motor

- [x] 1.1 `services/enercheck.py`:
  - helper de reparto por mayor resto (`floor` más un peso a las mayores fracciones, también con montos negativos);
  - cuota fija redondeada e igual para todas;
  - variable por mayor resto;
  - energía = total por mayor resto − fija − variable, repartida solo entre parcelas con consumo, o en partes iguales si nadie consumió.

  Verificar con pytest:
  - el cuadre es exacto (igualdad) en los escenarios de `test_motor.py` y en casos de fracciones adversas (3 parcelas iguales, consumos con decimales, descuentos negativos, una parcela sin consumo);
  - la parcela sin consumo solo paga la cuota fija;
  - la suite completa queda en verde.

## 2. Documentación

- [x] 2.1 `CLAUDE.md` (Motor EnerCheck: reparto por mayor resto) y `docs/flujo-periodo.md` (la invariante, ahora al peso). Verificar con `openspec validate cuadre-al-peso --strict`.
