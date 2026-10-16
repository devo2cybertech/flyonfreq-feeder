import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Clean(unittest.TestCase):
    def test_nothing_personal_or_secret_is_in_the_repository(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_repo.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
