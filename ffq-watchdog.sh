#!/bin/sh
# flyonfreq feeder watchdog (optional). Runs once a minute from ffq-watchdog.timer.
# It looks at two things: can this computer reach the internet, and is the sender (ffq-push) running?
#   - sender stopped for 5 minutes in a row: it starts the sender again.
#   - a problem (no internet, or the sender still stopped) for 30 minutes in a row: it restarts the computer, at most once an hour.
# It never looks at flyonfreq itself, so a problem on our side can never make your computer restart. It sends nothing anywhere except one tiny ping to public internet addresses.
# Change the 30 minutes with FFQ_WATCHDOG_MINUTES in /etc/ffq-push.env. Remove it with: sudo ./uninstall.sh
STATE="${FFQ_WD_STATE:-/var/lib/ffq-watchdog}"
LIMIT="${FFQ_WATCHDOG_MINUTES:-30}"
case "$LIMIT" in ''|*[!0-9]*) LIMIT=30;; esac
[ "$LIMIT" -ge 10 ] || LIMIT=10          # never faster than 10 minutes: a short outage must not cause a restart
SYSTEMCTL="${FFQ_WD_SYSTEMCTL:-systemctl}"
PING="${FFQ_WD_PING:-ping -c 1 -W 3}"
NOW="${FFQ_WD_NOW:-$(date +%s)}"
mkdir -p "$STATE"
FAILS="$STATE/fails"; LAST="$STATE/last-reboot"

online() { for ip in 1.1.1.1 9.9.9.9 8.8.8.8; do $PING "$ip" >/dev/null 2>&1 && return 0; done; return 1; }
sender_ok() { $SYSTEMCTL is-active --quiet ffq-push; }

if online && sender_ok; then echo 0 > "$FAILS"; exit 0; fi

n=$(( $(cat "$FAILS" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$FAILS"
logger -t ffq-watchdog "problem: $n minute(s) in a row (internet: $(online && echo ok || echo down), sender: $(sender_ok && echo running || echo stopped))" 2>/dev/null
if [ "$n" -eq 5 ] && ! sender_ok; then
  logger -t ffq-watchdog "starting the sender again" 2>/dev/null
  $SYSTEMCTL restart ffq-push
fi
[ "$n" -lt "$LIMIT" ] && exit 0
prev=$(cat "$LAST" 2>/dev/null || echo 0)
if [ $((NOW - prev)) -ge 3600 ]; then
  echo "$NOW" > "$LAST"; echo 0 > "$FAILS"
  logger -t ffq-watchdog "restarting the computer after $n minutes of problems" 2>/dev/null
  ${FFQ_WD_REBOOT:-$SYSTEMCTL reboot}
fi
