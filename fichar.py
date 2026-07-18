#!/usr/bin/env python3
"""
Autofichaje netTime + aviso de excepciones por email.

Uso:
    python fichar.py entrada
    python fichar.py salida

El script:
  1. Calcula la hora actual en Europe/Madrid (gestiona el cambio de hora solo).
  2. Si hoy es festivo o vacaciones (ver festivos.py / vacaciones.txt), NO ficha
     y (solo en la ejecucion "entrada") manda un email avisando.
  3. Si no, espera hasta la hora exacta objetivo y ficha en netTime.
"""

import os
import sys
import time
import smtplib
from datetime import datetime, date
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from festivos import FESTIVOS_2026

MADRID = ZoneInfo("Europe/Madrid")

# --- Configuración desde variables de entorno (GitHub Secrets) ---
NETTIME_URL = os.environ["NETTIME_URL"]
NETTIME_USER = os.environ["NETTIME_USER"]
NETTIME_PASS = os.environ["NETTIME_PASS"]

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_APP_PASSWORD = os.environ["EMAIL_APP_PASSWORD"]
EMAIL_TO = os.environ.get("EMAIL_TO", EMAIL_FROM)


def cargar_vacaciones():
    """Lee vacaciones.txt: una fecha YYYY-MM-DD por línea, '#' para comentarios."""
    fechas = set()
    try:
        with open("vacaciones.txt", encoding="utf-8") as f:
            for linea in f:
                linea = linea.split("#")[0].strip()
                if linea:
                    fechas.add(date.fromisoformat(linea))
    except FileNotFoundError:
        pass
    return fechas


def es_dia_excepcion(hoy: date):
    if hoy in FESTIVOS_2026:
        return "festivo"
    if hoy in cargar_vacaciones():
        return "vacaciones"
    return None


def enviar_email(asunto: str, cuerpo: str):
    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        server.send_message(msg)


def hora_objetivo(evento: str, hoy: date) -> datetime:
    """Devuelve el datetime (Madrid) al que hay que fichar hoy."""
    es_viernes = hoy.weekday() == 4  # lunes=0 ... viernes=4
    if evento == "entrada":
        h, m = 8, 0
    else:  # salida
        h, m = (14, 0) if es_viernes else (17, 0)
    return datetime.combine(hoy, datetime.min.time(), tzinfo=MADRID).replace(hour=h, minute=m)


def esperar_hasta(objetivo: datetime):
    ahora = datetime.now(MADRID)
    segundos = (objetivo - ahora).total_seconds()
    if segundos > 0:
        # margen de seguridad: no esperar más de 90 min (evita quedarse colgado si algo falla)
        time.sleep(min(segundos, 90 * 60))


def fichar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NETTIME_URL)

        # --- PLACEHOLDER: ajustar estos selectores con playwright codegen (ver README) ---
        page.fill("#usuario", NETTIME_USER)
        page.fill("#password", NETTIME_PASS)
        page.click("#botonLogin")
        page.wait_for_load_state("networkidle")
        page.click("#botonFichar")
        # -----------------------------------------------------------------------------

        page.wait_for_timeout(3000)
        browser.close()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("entrada", "salida"):
        print("Uso: python fichar.py [entrada|salida]")
        sys.exit(1)

    evento = sys.argv[1]
    hoy = datetime.now(MADRID).date()

    excepcion = es_dia_excepcion(hoy)
    if excepcion:
        if evento == "entrada":
            enviar_email(
                f"netTime: hoy no ficho ({excepcion})",
                f"Hoy {hoy.isoformat()} es {excepcion}, así que no se va a fichar automáticamente.",
            )
        print(f"Día de excepción ({excepcion}), no se ficha.")
        return

    objetivo = hora_objetivo(evento, hoy)
    esperar_hasta(objetivo)
    fichar()
    print(f"Fichaje de {evento} realizado a las {datetime.now(MADRID)}")


if __name__ == "__main__":
    main()
