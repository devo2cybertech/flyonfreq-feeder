# Changelog

## 1.1.0 - 2026-11-05
Optional watchdog (asked at install, default no): starts the sender again after 5 minutes stopped, restarts the computer after 30 minutes offline or stuck, at most once an hour, never depends on flyonfreq. The sender itself is unchanged.

## 1.0.0 - 2026-10-15
First public release. Sends the aircraft list of a readsb or dump1090 receiver every 2 seconds over one HTTPS connection. Sender protocol version 3. Includes `--dry-run`, an installer that verifies the checksum and asks for the key hidden, an uninstaller, and tests.
