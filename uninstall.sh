#!/bin/bash
# Removes the flyonfreq sender completely, or puts an earlier install back.
#   sudo ./uninstall.sh                      remove the service, the program and your key file
#   sudo ./uninstall.sh --restore FOLDER     go back to what install.sh saved in FOLDER (/etc/ffq-push.backup-DATE)
set -euo pipefail
ROOT="${FFQ_ROOT:-}"
[ -n "$ROOT" ] || [ "$(id -u)" -eq 0 ] || { echo "Run this as root: sudo ./uninstall.sh" >&2; exit 1; }
ENV_FILE="$ROOT/etc/ffq-push.env"; UNIT="$ROOT/etc/systemd/system/ffq-push.service"; DEST="$ROOT/opt/ffq"; OLD_BIN="$ROOT/usr/local/bin/ffq-push.py"
SYSTEMD=1; [ -n "${FFQ_SKIP_SYSTEMD:-}" ] && SYSTEMD=0

if [ "${1:-}" = "--restore" ]; then
  B="${2:-}"; [ -d "$B" ] || { echo "Give the backup folder, for example: sudo ./uninstall.sh --restore /etc/ffq-push.backup-20261016-091500" >&2; exit 1; }
  [ "$SYSTEMD" -eq 1 ] && systemctl stop ffq-push 2>/dev/null || true
  for pair in "etc_ffq-push.env:$ENV_FILE" "etc_systemd_system_ffq-push.service:$UNIT" "usr_local_bin_ffq-push.py:$OLD_BIN" "opt_ffq_ffq-push.py:$DEST/ffq-push.py"; do
    src="$B/${pair%%:*}"; dst="${pair#*:}"; [ -e "$src" ] && { mkdir -p "$(dirname "$dst")"; cp -p "$src" "$dst"; echo "restored $dst"; }
  done
  [ -e "$B/opt_ffq_ffq-push.py" ] || rm -rf "$DEST"
  if [ "$SYSTEMD" -eq 1 ]; then systemctl daemon-reload; systemctl restart ffq-push && echo "restarted the service you had before."; fi
  exit 0
fi

[ "$SYSTEMD" -eq 1 ] && { systemctl disable --now ffq-push 2>/dev/null || true; }
rm -f "$UNIT" "$ENV_FILE" "$OLD_BIN"
rm -rf "$DEST"
[ "$SYSTEMD" -eq 1 ] && systemctl daemon-reload
echo "Removed. Nothing of the sender is left on this machine. (Your readsb or dump1090 is untouched. Backups made by install.sh stay in /etc/ffq-push.backup-*: delete them if you do not want them.)"
