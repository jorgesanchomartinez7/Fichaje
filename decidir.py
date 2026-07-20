#!/usr/bin/env python3
"""
Decide si, en este preciso momento, toca fichar entrada, salida, o ninguna
de las dos (fuera de ventana horaria). Pensado para ejecutarse cada pocos
minutos y ser tolerante a que algún disparo de GitHub Actions se retrase.

Imprime por stdout una sola palabra: "entrada", "salida" o "none".
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

# Tolerancia: se considera "toca fichar" desde 2 min antes del objetivo
# hasta 20 min después (así, aunque GitHub Actions se retrase, lo pilla).
MARGEN_ANTES_MIN = 2
MARGEN_DESPUES_MIN = 20


def hora_objetivo(evento: str, hoy: date) -> datetime:
    es_viernes = hoy.weekday() == 4
    if evento == "entrada":
        h, m = 8, 0
    else:
        h, m = (14, 0) if es_viernes else (17, 0)
    return datetime.combine(hoy, datetime.min.time(), tzinfo=MADRID).replace(hour=h, minute=m)


def main():
    ahora = datetime.now(MADRID)
    hoy = ahora.date()

    if hoy.weekday() >= 5:  # sábado o domingo
        print("none")
        return

    for evento in ("entrada", "salida"):
        objetivo = hora_objetivo(evento, hoy)
        minutos_desde_objetivo = (ahora - objetivo).total_seconds() / 60
        if -MARGEN_ANTES_MIN <= minutos_desde_objetivo <= MARGEN_DESPUES_MIN:
            print(evento)
            return

    print("none")


if __name__ == "__main__":
    main()
