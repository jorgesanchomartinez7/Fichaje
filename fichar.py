#!/usr/bin/env python3
"""
Autofichaje netTime + aviso por email en cada fichaje y en días de excepción.

Uso:
    python fichar.py entrada
    python fichar.py salida
    python fichar.py entrada now   # modo prueba: salta la espera y la comprobación de excepción

El script:
  1. Calcula la hora actual en Europe/Madrid (gestiona el cambio de hora solo).
  2. Si hoy es festivo (festivos.py) o vacaciones (vacaciones.txt y/o Google Sheet),
     NO ficha y (solo en la ejecución "entrada") manda un email avisando.
  3. Si no, espera hasta la hora exacta objetivo, ficha en netTime, y manda un
     email confirmando que se ha fichado.
"""

import os
import sys
import time
import smtplib
import urllib.request
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

# Opcional: URL de "Publicar en la web" (CSV) de una Google Sheet con fechas de vacaciones
VACACIONES_SHEET_CSV_URL = os.environ.get("VACACIONES_SHEET_CSV_URL", "")


def cargar_vacaciones():
    """Junta fechas de vacaciones.txt (local) y de la Google Sheet (si está configurada)."""
    fechas = set()

    try:
        with open("vacaciones.txt", encoding="utf-8") as f:
            for linea in f:
                linea = linea.split("#")[0].strip()
                if linea:
                    fechas.add(date.fromisoformat(linea))
    except FileNotFoundError:
        pass

    if VACACIONES_SHEET_CSV_URL:
        try:
            with urllib.request.urlopen(VACACIONES_SHEET_CSV_URL, timeout=15) as resp:
                contenido = resp.read().decode("utf-8")
            for linea in contenido.splitlines():
                for celda in linea.split(","):
                    celda = celda.strip().strip('"')
                    if not celda:
                        continue
                    try:
                        fechas.add(date.fromisoformat(celda))
                    except ValueError:
                        pass  # ignora cabeceras o celdas que no son fechas
        except Exception as e:
            print(f"Aviso: no se pudo leer la Google Sheet de vacaciones ({e})")

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
        time.sleep(min(segundos, 90 * 60))  # margen: nunca más de 90 min


def fichar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NETTIME_URL)

        # --- Login: usuario = primer input que no es de tipo password ---
        page.locator('input:not([type="password"])').first.fill(NETTIME_USER)
        page.locator('input[type="password"]').fill(NETTIME_PASS)
        page.get_by_role("button", name="Login").click()

        # Esperar a que cargue el panel principal ("Marcaje remoto")
        page.wait_for_selector("text=Marcaje remoto", timeout=20000)

        # Abrir el desplegable de "Incidencia" y confirmar "Sin incidencia"
        page.locator("text=Sin incidencia").first.click()
        page.wait_for_timeout(800)
        page.get_by_text("Sin incidencia", exact=True).last.click()
        page.wait_for_timeout(500)

        # Marcar (el botón alterna solo entre entrada y salida)
        page.get_by_role("button", name="Marcar").click()
        # -------------------------------------------------------------

        page.wait_for_timeout(3000)
        browser.close()


def main():
    if len(sys.argv) not in (2, 3) or sys.argv[1] not in ("entrada", "salida"):
        print("Uso: python fichar.py [entrada|salida] [now]")
        sys.exit(1)

    evento = sys.argv[1]
    modo_prueba = len(sys.argv) == 3 and sys.argv[2] == "now"
    hoy = datetime.now(MADRID).date()

    if not modo_prueba:
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

    try:
        fichar()
    except Exception as e:
        enviar_email(
            f"netTime: ERROR al fichar ({evento})",
            f"Algo ha fallado al intentar fichar la {evento} el {hoy.isoformat()}.\n\nError: {e}",
        )
        raise

    hora_actual = datetime.now(MADRID).strftime("%H:%M")
    enviar_email(
        f"netTime: {evento} fichada ✅",
        f"Fichaje de {evento} realizado correctamente a las {hora_actual} del {hoy.isoformat()}.",
    )
    print(f"Fichaje de {evento} realizado a las {datetime.now(MADRID)} (modo_prueba={modo_prueba})")


if __name__ == "__main__":
    main()
