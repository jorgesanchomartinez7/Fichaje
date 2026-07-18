# Autofichaje netTime

Automatiza el fichaje en netTime (L-J 8:00-17:00, V 8:00-14:00) y te avisa por
email los días que no vas a fichar (festivos o vacaciones). Corre en la nube
(GitHub Actions), así que no depende de que tengas el móvil ni el ordenador
encendidos.

## 1. Subir esto a GitHub

1. Crea una cuenta en [github.com](https://github.com) si no tienes.
2. Crea un repositorio nuevo, **público** (así evitas los límites de minutos
   gratis de los repos privados — tus contraseñas van aparte, en "Secrets",
   y nunca se ven en el código ni en los logs).
3. Sube todo el contenido de esta carpeta (`fichar.py`, `festivos.py`,
   `vacaciones.txt`, `.github/workflows/fichar.yml`) a ese repositorio.

## 2. Configurar los "Secrets" (tus credenciales)

En el repositorio: **Settings → Secrets and variables → Actions → New
repository secret**. Crea estos 6:

| Nombre | Valor |
|---|---|
| `NETTIME_URL` | `https://c567.ntone.gospec.net/login.html?q=30994` |
| `NETTIME_USER` | tu usuario de netTime |
| `NETTIME_PASS` | tu contraseña de netTime |
| `EMAIL_FROM` | tu email de Gmail (el que envía los avisos) |
| `EMAIL_APP_PASSWORD` | una "contraseña de aplicación" de Gmail (ver abajo) |
| `EMAIL_TO` | el email donde quieres recibir los avisos (puede ser el mismo) |

**Cómo generar la contraseña de aplicación de Gmail:**
1. Activa la verificación en dos pasos en tu cuenta de Google (si no la
   tienes ya).
2. Ve a https://myaccount.google.com/apppasswords
3. Crea una nueva, ponle un nombre (ej. "netTime bot") y copia el código de
   16 caracteres que te da — eso es lo que pones en `EMAIL_APP_PASSWORD`
   (no tu contraseña normal de Gmail).

## 3. Ajustar los selectores del formulario (el paso importante)

No he podido ver el HTML exacto de tu netTime porque la página se carga con
JavaScript. En `fichar.py` he dejado unos selectores de ejemplo
(`#usuario`, `#password`, `#botonLogin`, `#botonFichar`) que casi seguro hay
que cambiar. Para sacar los correctos, en tu ordenador (una sola vez):

```bash
pip install playwright
playwright install chromium
playwright codegen https://c567.ntone.gospec.net/login.html?q=30994
```

Esto abre un navegador de verdad y una ventana al lado que va grabando en
código Python cada clic que haces. Simplemente:
1. Inicia sesión con tu usuario y contraseña.
2. Pulsa el botón de fichar.
3. Cierra la ventana.

Copia las líneas que generó (algo como `page.fill("#loginUser", "...")`,
`page.click("text=Entrar")`, etc.) y sustituye el bloque marcado como
`PLACEHOLDER` dentro de la función `fichar()` en `fichar.py`. Sube el cambio
a GitHub y ya está listo.

## 4. Probar antes de dejarlo en automático

En GitHub, ve a la pestaña **Actions → Autofichaje netTime → Run workflow**
para lanzarlo a mano y comprobar que ficha bien y que el email de prueba (si
fuerzas una fecha festiva en `vacaciones.txt`) llega correctamente.

## 5. Mantenimiento

- **Cada año** hay que actualizar `festivos.py` con el calendario laboral
  nuevo (se publica en el DOGV a mitad del año anterior).
- **Vacaciones**: añade la fecha en `vacaciones.txt` (formato `YYYY-MM-DD`,
  una por línea) cuando sepas que vas a librar. Recibirás el aviso por email
  automáticamente ese día en vez de que se intente fichar.
- El horario (L-J 8-17, V 8-14) está fijo en `fichar.py` en la función
  `hora_objetivo`; si algún día cambia tu jornada, se edita ahí.
