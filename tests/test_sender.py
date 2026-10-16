import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import importlib.util

spec = importlib.util.spec_from_file_location("ffq_push", ROOT / "ffq-push.py")
ffq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ffq)

PLANE = {"hex": "a1b2c3", "flight": "JBU123", "lat": 26.1, "lon": -80.2, "alt_baro": 3000, "gs": 150, "track": 90, "r": "N123AA", "t": "A320",
         "operator_note": "this field must never be sent", "wifi_password": "nope"}


class Trim(unittest.TestCase):
    def test_only_the_known_fields_are_sent(self):
        out = ffq.trim({"now": 1.0, "aircraft": [PLANE]})["aircraft"][0]
        self.assertEqual(out["hex"], "a1b2c3")
        self.assertNotIn("operator_note", out)
        self.assertNotIn("wifi_password", out)
        self.assertTrue(set(out) <= set(ffq.KEEP))

    def test_planes_without_a_position_or_with_a_made_up_address_are_not_sent(self):
        raw = {"aircraft": [dict(PLANE, hex="~abc123"), dict(PLANE, hex="abc"), dict(PLANE, lat=None), dict(PLANE, hex="d4e5f6")]}
        self.assertEqual([a["hex"] for a in ffq.trim(raw)["aircraft"]], ["d4e5f6"])

    def test_an_empty_or_broken_list_is_not_an_error(self):
        self.assertEqual(ffq.trim({})["aircraft"], [])
        self.assertEqual(ffq.trim({"aircraft": None})["aircraft"], [])


class Stats(unittest.TestCase):
    def test_the_numbers_about_the_sender_hold_no_place_and_no_name(self):
        allowed = {"version", "messages", "samples_processed", "samples_dropped", "max_distance_m", "load1", "uptime_s"}
        self.assertTrue(set(ffq.sender_stats()) <= allowed)


class DryRun(unittest.TestCase):
    def test_dry_run_needs_no_key_prints_what_would_be_sent_and_sends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "aircraft.json"
            src.write_text(json.dumps({"now": 1.0, "aircraft": [PLANE]}))
            env = {k: v for k, v in os.environ.items() if not k.startswith("FFQ_")}
            env["FFQ_SOURCE"] = str(src)
            r = subprocess.run([sys.executable, str(ROOT / "ffq-push.py"), "--dry-run"], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("would send 1 planes", r.stdout)
            self.assertNotIn("wifi_password", r.stdout)


class WhatTheProgramCanDo(unittest.TestCase):
    """The README promises these things; the tests keep the promises."""
    def setUp(self):
        self.source = (ROOT / "ffq-push.py").read_text()

    def test_it_makes_no_other_kind_of_connection_and_runs_no_commands(self):
        for forbidden in ("import socket", "subprocess", "os.system", "os.popen", "eval(", "exec(", "ftplib", "smtplib", "telnetlib"):
            self.assertNotIn(forbidden, self.source)

    def test_it_never_reads_the_receivers_location(self):
        self.assertNotIn("receiver.json", self.source)
        self.assertNotIn("receiver_lat", self.source)

    def test_it_only_talks_to_the_address_it_is_given(self):
        self.assertEqual(self.source.count("http.client.HTTPSConnection"), 1)


class Release(unittest.TestCase):
    def test_the_published_checksum_matches_the_program(self):
        line = (ROOT / "SHA256SUMS").read_text().split()
        self.assertEqual(line[1], "ffq-push.py")
        self.assertEqual(line[0], hashlib.sha256((ROOT / "ffq-push.py").read_bytes()).hexdigest(), "run: shasum -a 256 ffq-push.py > SHA256SUMS")

    def test_the_example_settings_hold_no_real_key(self):
        text = (ROOT / "ffq-push.env.example").read_text()
        self.assertIn("paste-your-key-here", text)


if __name__ == "__main__":
    unittest.main()
