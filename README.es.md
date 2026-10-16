# flyonfreq feeder

[English](README.md)

Un programa diminuto que envía a [flyonfreq](https://flyonfreq.com), un rastreador de vuelos para viajeros, la lista de aviones que oye tu receptor ADS-B. Donde no tenemos antena el mapa se ve vacío: **necesitamos antenas en cada lugar donde estés.**

Tu receptor queda exactamente como está. Este programa solo lee la lista que ya escribe y la envía por una conexión HTTPS normal. No hay que abrir nada en tu router.

- 96 líneas de Python simple, solo biblioteca estándar. Léelo: [`ffq-push.py`](ffq-push.py).
- Solo conexiones salientes, a una sola dirección: `https://api.flyonfreq.com`.
- Puedes ver exactamente qué enviaría antes de que envíe algo: `python3 /opt/ffq/ffq-push.py --dry-run`.

## Qué necesitas

- Un receptor con **readsb** (o dump1090-fa) que escriba un `aircraft.json` (una Raspberry Pi, una antena SDR y una antena de 1090 MHz).
- Python 3 y systemd (vienen con Raspberry Pi OS).
- Una **clave** para tu receptor. Pídela en la página Feed flyonfreq: <https://flyonfreq.com/feed>. Leemos cada solicitud; la clave llega cuando se aprueba. La clave es secreta: identifica a tu receptor.

## Instalar (unos cinco minutos)

```bash
git clone https://github.com/devo2cybertech/flyonfreq-feeder.git
cd flyonfreq-feeder
sudo ./install.sh
```

El script verifica el programa contra la suma de verificación publicada ([`SHA256SUMS`](SHA256SUMS)), encuentra tu `aircraft.json`, te pide la clave (se escribe oculta y nunca va en una línea de comandos), crea `/etc/ffq-push.env` (solo root puede leerlo), instala el servicio y lo inicia. Es corto: léelo primero si quieres.

Comprueba que funciona:

```bash
systemctl status ffq-push --no-pager
journalctl -u ffq-push -n 20 --no-pager
```

Si no hay líneas que digan `refused` o `failed`, está enviando. Tu receptor aparece en línea en tu página de estado en flyonfreq.com.

## Qué envía

Cada 2 segundos, una solicitud HTTPS con:

| Qué | Campos |
|---|---|
| Los aviones que oye tu receptor **con posición y una dirección de avión real** (los que no tienen posición o tienen una dirección inventada se dejan fuera) | `hex`, `flight` (indicativo), `r` (matrícula), `t` y `desc` (tipo), `category`, `ownOp` (operador), `dbFlags` |
| Dónde está cada avión y cómo se mueve | `lat`, `lon`, `alt_baro`, `alt_geom`, `gs`, `ias`, `tas`, `mach`, `track`, `true_heading`, `mag_heading`, `baro_rate`, `geom_rate`, `roll`, `track_rate`, `wd`, `ws`, `oat`, `tat` |
| Lo que dice el transpondedor | `squawk`, `emergency`, `nav_modes`, `nav_qnh`, `nav_altitude_mcp`, `nav_altitude_fms`, `nav_heading` |
| Qué tan bien lo oyó tu receptor | `rssi`, `messages`, `seen`, `seen_pos` |
| Números sobre el propio programa | su versión, mensajes del último minuto, muestras procesadas y perdidas, el avión más lejano en metros, la carga y el tiempo encendido de la Pi |

La lista de campos es la línea `KEEP` del programa. Cualquier otro campo que escriba tu receptor se descarta antes de enviar.

## Qué nunca envía

- **Tu ubicación.** El programa nunca lee la posición de tu receptor y no tiene dónde ponerla. Si elegiste compartir dónde está tu antena, lo hiciste en el formulario de solicitud, con tu consentimiento, y la mantenemos privada.
- Tu nombre, correo, datos de tu Wi-Fi o de tu red, ningún archivo aparte de la lista de aviones, ni nada de tus otros aparatos.
- No se envía nada a ninguna otra dirección.

Como en toda conexión de internet, nuestro servidor ve la dirección de red desde donde llega la solicitud. No la publicamos.

## Cuántos datos usa

Entre 1 y 3 kilobytes por envío en una zona tranquila, más cerca de un aeropuerto ocupado. Calcula **de 1 a 2 gigabytes al mes**. Si tu conexión tiene límite, pon `FFQ_EVERY=5` en `/etc/ffq-push.env` para enviar cada 5 segundos.

## Ajustes

`/etc/ffq-push.env` (ver [`ffq-push.env.example`](ffq-push.env.example)):

| Ajuste | Significado |
|---|---|
| `FFQ_URL` | A dónde enviar (ya viene lleno) |
| `FFQ_KEY` | Tu clave secreta. Nunca la compartas ni la pongas en un repositorio |
| `FFQ_SOURCE` | El `aircraft.json` de tu receptor: una ruta o una dirección como `http://localhost/tar1090/data/aircraft.json` |
| `FFQ_EVERY` | Segundos entre envíos (por defecto 2) |

Después de cambiarlo: `sudo systemctl restart ffq-push`.

## Actualizar, o reemplazar una instalación anterior

```bash
cd flyonfreq-feeder && git pull
sudo ./install.sh
```

Si ya hay un programa de envío instalado (incluso uno puesto con las instrucciones anteriores), el instalador **lo reemplaza, así que nunca hay más de uno funcionando**. Primero guarda tus archivos viejos en `/etc/ffq-push.backup-FECHA`, conserva tu clave y tus ajustes actuales (pulsa Enter en la pregunta de la clave) y borra la copia vieja del programa. Si algo sale mal puedes volver exactamente a lo que tenías:

```bash
sudo ./uninstall.sh --restore /etc/ffq-push.backup-FECHA
```

Si quieres estar seguro, compara el nuevo `SHA256SUMS` con la página de donde lo obtuviste.

## Desinstalar

```bash
sudo ./uninstall.sh
```

Esto quita el servicio, el programa y tu archivo de clave. Tu readsb no se toca. (Las copias de respaldo que hizo el instalador quedan en `/etc/ffq-push.backup-*`; bórralas si no las quieres.)

## Seguridad

El servicio corre como un usuario temporal sin derechos extra, con el sistema en solo lectura y sin nuevos privilegios. Si encuentras un problema de seguridad, usa el botón *Report a vulnerability* de este repositorio (reporte privado de GitHub) en lugar de un issue público. Si tu clave se filtra, avísanos en la página Feed flyonfreq y la reemplazaremos.

## Preguntas y problemas

Abre un issue aquí. Por favor no pegues tu clave en un issue.

## Licencia

MIT. Ver [`LICENSE`](LICENSE). Copyright 2026 O2CyberTech Inc.
