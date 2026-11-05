"""The optional watchdog, run against pretend commands: it can never restart the machine running the tests."""
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SH = ROOT / "ffq-watchdog.sh"


class Box:
    """A pretend computer: `online` and `sender` can be switched, and every restart or reboot is written down."""
    def __init__(self, online=True, sender=True, minutes=None):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.online, self.sender, self.minutes, self.now = online, sender, minutes, 10_000_000
        self.log = self.d / "log"
        (self.d / "bin").mkdir()
        (self.d / "systemctl").write_text('#!/bin/sh\ncase "$1" in is-active) [ -e "$FFQ_T/sender-up" ];; restart) echo restart >> "$FFQ_T/log"; touch "$FFQ_T/sender-up";; reboot) echo reboot >> "$FFQ_T/log";; esac\n')
        (self.d / "ping").write_text('#!/bin/sh\n[ -e "$FFQ_T/online" ]\n')
        (self.d / "reboot").write_text('#!/bin/sh\necho reboot >> "$FFQ_T/log"\n')
        for f in ("systemctl", "ping", "reboot"):
            (self.d / f).chmod(0o755)

    def tick(self, n=1):
        for _ in range(n):
            for name, on in (("online", self.online), ("sender-up", self.sender)):
                p = self.d / name
                p.touch() if on else (p.unlink() if p.exists() else None)
            env = dict(os.environ, FFQ_T=str(self.d), FFQ_WD_STATE=str(self.d / "state"), FFQ_WD_SYSTEMCTL=str(self.d / "systemctl"), FFQ_WD_PING=str(self.d / "ping"),
                       FFQ_WD_REBOOT=str(self.d / "reboot"), FFQ_WD_NOW=str(self.now))
            if self.minutes:
                env["FFQ_WATCHDOG_MINUTES"] = str(self.minutes)
            r = subprocess.run(["sh", str(SH)], env=env, capture_output=True, text=True, timeout=20)
            assert r.returncode == 0, r.stderr
            self.now += 60
            self.sender = (self.d / "sender-up").exists()

    def events(self):
        return self.log.read_text().split() if self.log.exists() else []


class Watchdog(unittest.TestCase):
    def test_a_healthy_computer_is_left_alone(self):
        b = Box()
        b.tick(60)
        self.assertEqual(b.events(), [])

    def test_a_short_outage_does_not_restart_anything(self):
        b = Box(online=False)
        b.tick(20)
        b.online = True
        b.tick(60)
        self.assertEqual(b.events(), [])

    def test_offline_for_30_minutes_restarts_the_computer_once_an_hour(self):
        b = Box(online=False)
        b.tick(29)
        self.assertEqual(b.events(), [])
        b.tick(1)
        self.assertEqual(b.events(), ["reboot"])
        b.tick(40)                      # still offline 40 minutes later: not again within the hour
        self.assertEqual(b.events(), ["reboot"])

    def test_a_stopped_sender_is_started_again_before_anything_is_restarted(self):
        b = Box(sender=False)
        b.tick(5)
        self.assertEqual(b.events(), ["restart"])
        b.tick(60)
        self.assertEqual(b.events(), ["restart"])      # it came back: no reboot

    def test_the_limit_can_be_raised_but_never_below_ten_minutes(self):
        b = Box(online=False, minutes=60)
        b.tick(59)
        self.assertEqual(b.events(), [])
        b.tick(1)
        self.assertEqual(b.events(), ["reboot"])
        c = Box(online=False, minutes=2)
        c.tick(9)
        self.assertEqual(c.events(), [])
        c.tick(1)
        self.assertEqual(c.events(), ["reboot"])

    def test_it_never_looks_at_flyonfreq(self):
        text = SH.read_text()
        self.assertNotIn("flyonfreq.com", text)
        self.assertNotIn("curl", text)


class Installer(unittest.TestCase):
    def _run(self, script, fake, stdin, **extra):
        env = dict(os.environ, FFQ_ROOT=str(fake), FFQ_SKIP_SYSTEMD="1", **extra)
        return subprocess.run(["bash", str(ROOT / script), *([] if script == "install.sh" else [])], input=stdin, capture_output=True, text=True, env=env, timeout=60)

    def _world(self):
        fake = pathlib.Path(tempfile.mkdtemp())
        (fake / "run/readsb").mkdir(parents=True)
        (fake / "run/readsb/aircraft.json").write_text('{"aircraft": []}')
        return fake

    def test_default_is_no_watchdog_and_yes_installs_it_and_uninstall_removes_it(self):
        key = "K" * 12 + "secret-key-0123456789"
        fake = self._world()
        r = self._run("install.sh", fake, key + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((fake / "etc/systemd/system/ffq-watchdog.timer").exists())
        fake = self._world()
        r = self._run("install.sh", fake, key + "\n", FFQ_WATCHDOG="y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((fake / "etc/systemd/system/ffq-watchdog.timer").exists())
        self.assertTrue((fake / "opt/ffq/ffq-watchdog.sh").exists())
        u = self._run("uninstall.sh", fake, "")
        self.assertEqual(u.returncode, 0, u.stderr)
        self.assertFalse((fake / "etc/systemd/system/ffq-watchdog.timer").exists())
        self.assertFalse((fake / "opt/ffq").exists())


if __name__ == "__main__":
    unittest.main()
