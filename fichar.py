#!/usr/bin/env python3
"""
Autofichaje netTime + aviso por email en cada fichaje y en días de excepción.

Uso:
    python fichar.py entrada
    python fichar.py salida

El script:
  1. Si hoy es festivo (festivos.py) o vacaciones (vacaciones.txt y/o Google Sheet),
     NO ficha y (solo en la ejecución "entrada") manda un email avisando.
  2. Si no, ficha en netTime y manda un email confirmando que se ha fichado.

(El cuándo lanzarlo lo decide decidir.py + el workflow, este script ya no espera.)
"""

import os
import sys
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


def fichar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NETTIME_URL)
        page.screenshot(path="debug_1_login.png")

        # --- Login: usuario = primer input que no es de tipo password ---
        page.locator('input:not([type="password"])').first.fill(NETTIME_USER)
        page.locator('input[type="password"]').fill(NETTIME_PASS)
        page.get_by_role("button", name="Login").click()

        # Esperar a que cargue el panel principal ("Marcaje remoto")
        page.wait_for_selector("text=Marcaje remoto", timeout=20000)
        page.screenshot(path="debug_2_panel.png")

# Abrir el desplegable de "Incidencia" (usamos la clase exacta del
        # cuadro, .ib-value, porque el texto "Sin incidencia" aparece
        # también en "Estado actual" y hacía clic en el sitio equivocado)
        page.locator(".ib-value").first.click()
        page.wait_for_timeout(800)
        page.screenshot(path="debug_3_desplegable_abierto.png")

        try:
            buscador = page.get_by_placeholder("Buscar...")
            buscador.click(timeout=5000)
            buscador.fill("Sin incidencia")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
        except Exception as e:
            print(f"Aviso: no se pudo confirmar 'Sin incidencia' con el buscador: {e}")
            page.keyboard.press("Escape")

        page.wait_for_timeout(500)
        page.screenshot(path="debug_4_antes_de_marcar.png")

# Marcar (el botón alterna solo entre entrada y salida)
        page.get_by_role("button", name="Marcar").click(timeout=10000)
        # -------------------------------------------------------------

        page.wait_for_timeout(3000)
        page.screenshot(path="debug_5_final.png")
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
    print(f"Fichaje de {evento} realizado a las {datetime.now(MADRID)}")


if __name__ == "__main__":
    main()
