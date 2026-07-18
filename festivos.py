"""
Festivos 2026 - Comunidad Valenciana + festivos locales ciudad de Valencia.
Fuente: Decreto 100/2025 del Consell (DOGV) y resolución de festivos locales.
Actualizar cada año (normalmente se publican en el DOGV a mitad del año anterior).
"""

from datetime import date

FESTIVOS_2026 = {
    date(2026, 1, 1),   # Año Nuevo
    date(2026, 1, 6),   # Epifanía del Señor
    date(2026, 1, 22),  # San Vicente Mártir (local Valencia ciudad)
    date(2026, 3, 19),  # San José
    date(2026, 4, 3),   # Viernes Santo
    date(2026, 4, 6),   # Lunes de Pascua
    date(2026, 4, 13),  # San Vicente Ferrer (local Valencia ciudad)
    date(2026, 5, 1),   # Fiesta del Trabajo
    date(2026, 6, 24),  # San Juan
    date(2026, 8, 15),  # Asunción de la Virgen (cae en sábado en 2026)
    date(2026, 10, 9),  # Día de la Comunitat Valenciana
    date(2026, 10, 12), # Fiesta Nacional de España
    date(2026, 12, 8),  # Inmaculada Concepción
    date(2026, 12, 25), # Navidad
}
