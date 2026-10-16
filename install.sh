#!/bin/bash
# Installs (or updates) the flyonfreq sender on a Raspberry Pi or any Linux box that already runs readsb or dump1090.
# Run it from the folder you downloaded:   sudo ./install.sh
# What it does: checks the program against SHA256SUMS, saves anything already installed to a backup folder, copies the program to /opt/ffq, keeps your current key and
# settings if there are any (or asks for your key, typed hidden, never put on a command line), writes /etc/ffq-push.env (only root can read it), installs the service
# and starts it. If an older copy of the sender is found, it is replaced: there is never more than one sender running. Read it first: it is short.
set -euo pipefail

ROOT="${FFQ_ROOT:-}"      # empty on a real machine (the tests point it at a folder)
ENV_FILE="$ROOT/etc/ffq-push.env"
UNIT="$ROOT/etc/systemd/system/ffq-push.service"
DEST="$ROOT/opt/ffq"
OLD_BIN="$ROOT/usr/local/bin/ffq-push.py"      # where the first version of the instructions put it

[ -n "$ROOT" ] || [ "$(id -u)" -eq 0 ] || { echo "Run this as root: sudo ./install.sh" >&2; exit 1; }
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "python3 is required (it comes with Raspberry Pi OS)." >&2; exit 1; }
SYSTEMD=1
if [ -n "${FFQ_SKIP_SYSTEMD:-}" ]; then SYSTEMD=0; else command -v systemctl >/dev/null || { echo "systemd is required." >&2; exit 1; }; fi

echo "1/6 Checking that the program is the one we published..."
if command -v sha256sum >/dev/null; then
  sha256sum -c SHA256SUMS --ignore-missing || { echo "The checksum does not match. Do not install: download the files again from the official page." >&2; exit 1; }
else
  echo "    sha256sum not found: skipping the check (install coreutils to enable it)."
fi

echo "2/6 Looking for an earlier install..."
EXISTING_KEY="" EXISTING_SOURCE="" EXISTING_EVERY=""
if [ -r "$ENV_FILE" ]; then
  EXISTING_KEY="$(grep -m1 '^FFQ_KEY=' "$ENV_FILE" | cut -d= -f2- || true)"
  EXISTING_SOURCE="$(grep -m1 '^FFQ_SOURCE=' "$ENV_FILE" | cut -d= -f2- || true)"
  EXISTING_EVERY="$(grep -m1 '^FFQ_EVERY=' "$ENV_FILE" | cut -d= -f2- || true)"
fi
BACKUP=""
if [ -e "$ENV_FILE" ] || [ -e "$UNIT" ] || [ -e "$OLD_BIN" ] || [ -e "$DEST/ffq-push.py" ]; then
  BACKUP="$ROOT/etc/ffq-push.backup-$(date +%Y%m%d-%H%M%S)"
  mkdir -m 700 -p "$BACKUP"
  for f in "$ENV_FILE" "$UNIT" "$OLD_BIN" "$DEST/ffq-push.py"; do [ -e "$f" ] && cp -p "$f" "$BACKUP/$(echo "${f#"$ROOT"}" | tr '/' '_' | sed 's/^_//')"; done
  chmod 600 "$BACKUP"/* 2>/dev/null || true
  echo "    found an earlier install: your files are saved in $BACKUP"
else
  echo "    none: this is a fresh install."
fi

echo "3/6 Finding your receiver's aircraft list..."
SOURCE=""
if [ -n "$EXISTING_SOURCE" ] && { [ -r "$ROOT$EXISTING_SOURCE" ] || [[ "$EXISTING_SOURCE" == http* ]]; }; then
  SOURCE="$EXISTING_SOURCE"; echo "    keeping the one you already use: $SOURCE"
else
  for f in /run/readsb/aircraft.json /run/dump1090-fa/aircraft.json /run/dump1090/aircraft.json /var/run/readsb/aircraft.json; do
    [ -r "$ROOT$f" ] && SOURCE="$f" && break
  done
  if [ -z "$SOURCE" ]; then
    read -rp "    I could not find aircraft.json. Where is it (a path like /run/readsb/aircraft.json, or an address like http://localhost/tar1090/data/aircraft.json)? " SOURCE
  fi
  echo "    using $SOURCE"
fi
case "$SOURCE" in /*|http://*|https://*) ;; *) echo "That does not look like a path or an address." >&2; exit 1;; esac

echo "4/6 Your secret key."
KEY=""
if [[ "$EXISTING_KEY" =~ ^[A-Za-z0-9_-]{20,80}$ ]]; then
  read -rsp "    Press Enter to keep your current key, or paste a new one (typed hidden): " KEY; echo
  [ -n "$KEY" ] || KEY="$EXISTING_KEY"
else
  read -rsp "    Paste the key from the Feed flyonfreq page (typed hidden): " KEY; echo
fi
[[ "$KEY" =~ ^[A-Za-z0-9_-]{20,80}$ ]] || { echo "That does not look like a key (20 to 80 letters, digits, - or _). Nothing was changed except the backup." >&2; exit 1; }

echo "5/6 Installing..."
install -d -m 755 "$DEST"
install -m 755 ffq-push.py "$DEST/ffq-push.py"
mkdir -p "$(dirname "$ENV_FILE")"
umask 077
{
  echo "FFQ_URL=https://api.flyonfreq.com/api/tracking/receiver/push"
  echo "FFQ_KEY=$KEY"
  echo "FFQ_SOURCE=$SOURCE"
  [ -n "$EXISTING_EVERY" ] && echo "FFQ_EVERY=$EXISTING_EVERY"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"
[ -n "$ROOT" ] || chown root:root "$ENV_FILE"
install -d -m 755 "$(dirname "$UNIT")"
install -m 644 ffq-push.service "$UNIT"

echo "6/6 Starting..."
if [ "$SYSTEMD" -eq 1 ]; then
  systemctl daemon-reload
  systemctl enable ffq-push >/dev/null 2>&1 || true
  systemctl restart ffq-push
  sleep 3
  if systemctl is-active --quiet ffq-push; then
    echo "    running."
    if [ -e "$OLD_BIN" ]; then rm -f "$OLD_BIN"; echo "    removed the old copy of the program ($OLD_BIN): the new one replaced it."; fi
  else
    echo "    The service did not start. See: journalctl -u ffq-push -n 20 --no-pager" >&2
    [ -z "$BACKUP" ] || echo "    To go back to what you had: sudo ./uninstall.sh --restore \"$BACKUP\"" >&2
    exit 1
  fi
  systemctl --no-pager --lines=6 status ffq-push || true
else
  [ -e "$OLD_BIN" ] && rm -f "$OLD_BIN"
fi
echo
echo "Done. Watch it:   journalctl -u ffq-push -f        See what it sends:   python3 $DEST/ffq-push.py --dry-run"
[ -z "$BACKUP" ] || echo "Your previous files: $BACKUP   (go back with: sudo ./uninstall.sh --restore \"$BACKUP\")"
