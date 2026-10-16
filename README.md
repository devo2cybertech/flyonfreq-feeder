# flyonfreq feeder

[Español](README.es.md)

A tiny program that sends the aircraft list your ADS-B receiver hears to [flyonfreq](https://flyonfreq.com), a flight tracker for travelers. Where we have no antenna the map is thin: **we need antennas everywhere you are.**

You keep your receiver exactly as it is. This program only reads the list it already writes and sends it out over a normal HTTPS connection. Nothing to open on your router.

- 96 lines of plain Python, standard library only. Read it: [`ffq-push.py`](ffq-push.py).
- Outgoing connections only, to one address: `https://api.flyonfreq.com`.
- You can see exactly what it would send before it sends anything: `python3 /opt/ffq/ffq-push.py --dry-run`.

## What you need

- A receiver that runs **readsb** (or dump1090-fa) and writes an `aircraft.json` (a Raspberry Pi, an SDR stick and a 1090 MHz antenna).
- Python 3 and systemd (both come with Raspberry Pi OS).
- A **key** for your receiver. Ask for one on the Feed flyonfreq page: <https://flyonfreq.com/feed>. We read every request; the key arrives once it is approved. The key is secret: it identifies your receiver.

## Install (about five minutes)

```bash
git clone https://github.com/devo2cybertech/flyonfreq-feeder.git
cd flyonfreq-feeder
sudo ./install.sh
```

The script checks the program against the published checksum ([`SHA256SUMS`](SHA256SUMS)), finds your `aircraft.json`, asks for your key (typed hidden, never put on a command line), writes `/etc/ffq-push.env` (only root can read it), installs the service and starts it. It is short: read it first if you like.

Check that it works:

```bash
systemctl status ffq-push --no-pager
journalctl -u ffq-push -n 20 --no-pager
```

No lines saying `refused` or `failed` means it is sending. Your receiver shows as online on your status page at flyonfreq.com.

## What it sends

Every 2 seconds, one HTTPS request with:

| What | Fields |
|---|---|
| The planes your receiver hears **with a position and a real aircraft address** (planes without a position or with a made-up address are left out) | `hex`, `flight` (call sign), `r` (registration), `t` and `desc` (type), `category`, `ownOp` (operator), `dbFlags` |
| Where each plane is and how it moves | `lat`, `lon`, `alt_baro`, `alt_geom`, `gs`, `ias`, `tas`, `mach`, `track`, `true_heading`, `mag_heading`, `baro_rate`, `geom_rate`, `roll`, `track_rate`, `wd`, `ws`, `oat`, `tat` |
| What the transponder says | `squawk`, `emergency`, `nav_modes`, `nav_qnh`, `nav_altitude_mcp`, `nav_altitude_fms`, `nav_heading` |
| How well your receiver heard it | `rssi`, `messages`, `seen`, `seen_pos` |
| Numbers about the sender itself | its version, messages in the last minute, samples processed and dropped, the farthest plane in meters, the Pi's load and uptime |

The list of fields is the `KEEP` line of the program. Any other field your receiver writes is dropped before sending.

## What it never sends

- **Your location.** The program never reads your receiver's position and has no place to put one. If you chose to share where your antenna is, you did it on the application form, with your consent, and we keep it private.
- Your name, email, Wi-Fi or network details, any file other than the aircraft list, or anything about your other devices.
- Nothing is sent to any other address.

Like every connection on the internet, our server sees the network address the request comes from. We do not publish it.

## How much data

About 1 to 3 kilobytes per send near a quiet area, more near a busy airport. Plan on **1 to 2 gigabytes a month**. If your connection is metered, set `FFQ_EVERY=5` in `/etc/ffq-push.env` to send every 5 seconds instead.

## Settings

`/etc/ffq-push.env` (see [`ffq-push.env.example`](ffq-push.env.example)):

| Setting | Meaning |
|---|---|
| `FFQ_URL` | Where to send (already filled in) |
| `FFQ_KEY` | Your secret key. Never share it, never put it in a repository |
| `FFQ_SOURCE` | Your receiver's `aircraft.json`: a path, or an address such as `http://localhost/tar1090/data/aircraft.json` |
| `FFQ_EVERY` | Seconds between sends (default 2) |

After changing it: `sudo systemctl restart ffq-push`.

## Update, or replace an older install

```bash
cd flyonfreq-feeder && git pull
sudo ./install.sh
```

If a sender is already installed (including one set up with the older instructions), the installer **replaces it, so there is never more than one sender running**. It first saves your old files in `/etc/ffq-push.backup-DATE`, keeps your current key and settings (press Enter at the key question), and removes the old copy of the program. If anything goes wrong you can go back to exactly what you had:

```bash
sudo ./uninstall.sh --restore /etc/ffq-push.backup-DATE
```

Compare the new `SHA256SUMS` with the page you got it from if you want to be sure.

## Uninstall

```bash
sudo ./uninstall.sh
```

This removes the service, the program and your key file. Your readsb is untouched. (The backups made by the installer stay in `/etc/ffq-push.backup-*`; delete them if you do not want them.)

## Security

The service runs as a throw-away user with no extra rights, a read-only system and no new privileges. If you find a security problem, please use this repository's *Report a vulnerability* button (GitHub private reporting) instead of a public issue. If your key leaks, tell us through the Feed flyonfreq page and we will replace it.

## Questions and problems

Open an issue here. Please do not paste your key in an issue.

## License

MIT. See [`LICENSE`](LICENSE). Copyright 2026 O2CyberTech Inc.
