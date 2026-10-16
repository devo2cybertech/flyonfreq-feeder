"""The installer against a pretend file system (FFQ_ROOT) with systemd switched off: it can never touch the real machine running the tests."""
import glob
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = "K" * 12 + "secret-key-0123456789"
NEW_KEY = "N" * 12 + "another-key-0123456789"


def run(script, fake, stdin="", *args):
    env = dict(os.environ, FFQ_ROOT=str(fake), FFQ_SKIP_SYSTEMD="1")
    return subprocess.run(["bash", str(ROOT / script), *args], input=stdin, capture_output=True, text=True, env=env, timeout=60)


def world(with_old_install=False):
    d = tempfile.mkdtemp()
    fake = pathlib.Path(d)
    (fake / "run/readsb").mkdir(parents=True)
    (fake / "run/readsb/aircraft.json").write_text('{"aircraft": []}')
    if with_old_install:
        (fake / "etc/systemd/system").mkdir(parents=True)
        (fake / "usr/local/bin").mkdir(parents=True)
        (fake / "etc/ffq-push.env").write_text("FFQ_URL=https://api.flyonfreq.com/api/tracking/receiver/push\nFFQ_KEY=%s\nFFQ_SOURCE=/run/readsb/aircraft.json\nFFQ_EVERY=5\n" % KEY)
        (fake / "etc/systemd/system/ffq-push.service").write_text("[Service]\nExecStart=/usr/bin/python3 /usr/local/bin/ffq-push.py\n")
        (fake / "usr/local/bin/ffq-push.py").write_text("# the old sender\n")
    return fake


class Fresh(unittest.TestCase):
    def test_a_fresh_install_writes_a_private_key_file_and_never_prints_the_key(self):
        fake = world()
        r = run("install.sh", fake, NEW_KEY + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        env = fake / "etc/ffq-push.env"
        self.assertIn("FFQ_KEY=" + NEW_KEY, env.read_text())
        self.assertEqual(oct(env.stat().st_mode & 0o777), "0o600")
        self.assertTrue((fake / "opt/ffq/ffq-push.py").exists())
        self.assertIn("DynamicUser=yes", (fake / "etc/systemd/system/ffq-push.service").read_text())
        self.assertNotIn(NEW_KEY, r.stdout + r.stderr)
        self.assertIn("fresh install", r.stdout)

    def test_a_key_that_does_not_look_like_one_changes_nothing(self):
        fake = world()
        r = run("install.sh", fake, "short\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((fake / "etc/ffq-push.env").exists())


class Upgrade(unittest.TestCase):
    """What happens to a sender that is already installed (for example one set up with older instructions)?"""
    def test_the_old_install_is_replaced_not_duplicated_and_nothing_is_lost(self):
        fake = world(with_old_install=True)
        r = run("install.sh", fake, "\n")                                           # Enter: keep the current key
        self.assertEqual(r.returncode, 0, r.stderr)
        env = (fake / "etc/ffq-push.env").read_text()
        self.assertIn("FFQ_KEY=" + KEY, env)                                           # the same key
        self.assertIn("FFQ_EVERY=5", env)                                              # the person's own setting survives
        self.assertIn("FFQ_SOURCE=/run/readsb/aircraft.json", env)
        self.assertFalse((fake / "usr/local/bin/ffq-push.py").exists())                # the old program is gone: one sender only
        self.assertIn("/opt/ffq/ffq-push.py", (fake / "etc/systemd/system/ffq-push.service").read_text())
        backups = glob.glob(str(fake / "etc/ffq-push.backup-*"))
        self.assertEqual(len(backups), 1)
        saved = " ".join(os.listdir(backups[0]))
        self.assertIn("ffq-push.env", saved)
        self.assertIn("ffq-push.service", saved)
        self.assertIn("ffq-push.py", saved)
        self.assertNotIn(KEY, r.stdout + r.stderr)

    def test_a_new_key_can_be_pasted_instead_of_keeping_the_old_one(self):
        fake = world(with_old_install=True)
        r = run("install.sh", fake, NEW_KEY + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FFQ_KEY=" + NEW_KEY, (fake / "etc/ffq-push.env").read_text())

    def test_going_back_restores_exactly_what_was_there(self):
        fake = world(with_old_install=True)
        before_env = (fake / "etc/ffq-push.env").read_text()
        before_unit = (fake / "etc/systemd/system/ffq-push.service").read_text()
        run("install.sh", fake, "\n")
        backup = glob.glob(str(fake / "etc/ffq-push.backup-*"))[0]
        r = run("uninstall.sh", fake, "", "--restore", backup)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((fake / "etc/ffq-push.env").read_text(), before_env)
        self.assertEqual((fake / "etc/systemd/system/ffq-push.service").read_text(), before_unit)
        self.assertEqual((fake / "usr/local/bin/ffq-push.py").read_text(), "# the old sender\n")
        self.assertFalse((fake / "opt/ffq").exists())

    def test_running_the_installer_twice_is_harmless(self):
        fake = world(with_old_install=True)
        run("install.sh", fake, "\n")
        r = run("install.sh", fake, "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FFQ_KEY=" + KEY, (fake / "etc/ffq-push.env").read_text())


class Remove(unittest.TestCase):
    def test_uninstall_leaves_nothing_of_the_sender(self):
        fake = world(with_old_install=True)
        run("install.sh", fake, "\n")
        r = run("uninstall.sh", fake)
        self.assertEqual(r.returncode, 0, r.stderr)
        for p in ("etc/ffq-push.env", "etc/systemd/system/ffq-push.service", "usr/local/bin/ffq-push.py", "opt/ffq"):
            self.assertFalse((fake / p).exists(), p)


if __name__ == "__main__":
    unittest.main()
