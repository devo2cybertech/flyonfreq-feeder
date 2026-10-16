#!/usr/bin/env python3
"""Sends this receiver's aircraft list to flyonfreq every couple of seconds, so the receiver can sit on ANY network, with nothing to open on the router.

Runs on the Raspberry Pi next to readsb. Only makes outgoing https calls, so it needs nothing from the router. Python standard library only; one kept-open connection, so it is light on an old Pi.
Settings come from environment variables (set in /etc/ffq-push.env, see ffq-push.service):
    FFQ_URL     https://api.flyonfreq.com/api/tracking/receiver/push
    FFQ_KEY     the secret key for this receiver (never share it, never put it in a repository)
    FFQ_SOURCE  where readsb writes its list (default /run/readsb/aircraft.json)
    FFQ_EVERY   seconds between sends (default 2)
Run with --dry-run to print what would be sent (a few planes) without sending anything.
"""
import http.client
import json
import os
import sys
import time
import urllib.parse
import urllib.request

KEEP = ("hex", "flight", "r", "t", "desc", "lat", "lon", "alt_baro", "alt_geom", "gs", "track", "baro_rate", "category", "squawk", "dbFlags", "ownOp", "seen_pos", "seen", "mach", "ias", "tas", "true_heading", "mag_heading", "geom_rate", "roll", "track_rate", "nav_qnh", "nav_altitude_mcp", "nav_altitude_fms", "nav_heading", "nav_modes", "emergency", "rssi", "messages", "wd", "ws", "oat", "tat")


def read_source(source):
    if source.startswith("http"):
        return json.load(urllib.request.urlopen(source, timeout=5))
    with open(source) as f:
        return json.load(f)


def trim(raw):
    """Only what the server uses: planes with a position and a real ICAO address, and only the fields it reads. Keeps the message small."""
    out = []
    for a in raw.get("aircraft") or []:
        hex_ = str(a.get("hex") or "")
        if len(hex_) != 6 or hex_.startswith("~") or a.get("lat") is None or a.get("lon") is None:
            continue
        out.append({k: a[k] for k in KEEP if k in a})
    return {"now": raw.get("now"), "aircraft": out}


def sender_stats():
    """A few numbers about this receiver for the admin page: messages in the last minute, dropped samples, the farthest plane, how busy the Pi is. Numbers only, no place."""
    out = {"version": 3}
    try:
        l = json.load(open(os.environ.get("FFQ_STATS", "/run/readsb/stats.json")))["last1min"]
        out.update({"messages": l.get("messages"), "samples_processed": l["local"].get("samples_processed"), "samples_dropped": l["local"].get("samples_dropped"), "max_distance_m": l.get("max_distance")})
    except Exception:
        pass
    try:
        out["load1"] = os.getloadavg()[0]
        out["uptime_s"] = float(open("/proc/uptime").read().split()[0])
    except Exception:
        pass
    return {k: v for k, v in out.items() if v is not None}


def main():
    source = os.environ.get("FFQ_SOURCE", "/run/readsb/aircraft.json")
    every = float(os.environ.get("FFQ_EVERY", "2"))
    if "--dry-run" in sys.argv:
        body = trim(read_source(source))
        body["ffq"] = sender_stats()
        print("would send %d planes, %d bytes" % (len(body["aircraft"]), len(json.dumps(body))))
        print("about the sender:", json.dumps(body["ffq"]))
        print(json.dumps(body["aircraft"][:2], indent=1))
        return
    url, key = os.environ["FFQ_URL"], os.environ["FFQ_KEY"]
    parts = urllib.parse.urlsplit(url)
    conn = None
    while True:
        started = time.time()
        try:
            body = trim(read_source(source))
            body["ffq"] = sender_stats()
            data = json.dumps(body).encode()
            if conn is None:
                conn = (http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection)(parts.netloc, timeout=10)
            conn.request("POST", parts.path, body=data, headers={"Content-Type": "application/json", "X-Receiver-Key": key})
            resp = conn.getresponse()
            resp.read()
            if resp.status == 401:
                print("the server refused the key (401): check FFQ_KEY", file=sys.stderr)
            elif resp.status >= 400:
                print("the server answered %d" % resp.status, file=sys.stderr)
        except Exception as exc:  # no internet for a moment, readsb restarting: try again, never crash
            print("send failed: %s" % type(exc).__name__, file=sys.stderr)
            try:
                if conn:
                    conn.close()
            finally:
                conn = None
        time.sleep(max(0.5, every - (time.time() - started)))


if __name__ == "__main__":
    main()
