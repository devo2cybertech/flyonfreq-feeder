#!/usr/bin/env python3
"""Fails when something that must never be published is in the repository: an email address, a person's name, a data provider's name, or something that looks like a real key.
Run before every push: python3 tools/check_repo.py"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = {
    "an email address": re.compile(r"[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com)[A-Za-z0-9-]+\.[A-Za-z.]{2,}", re.I),
    "a person's name or school": re.compile(r"\b(oscar|ojeda|njit)\b", re.I),
    "a data provider's name": re.compile(r"adsb\.?lol|aerodatabox|rapidapi|opensky|airlabs|aviationstack|flightlabs|airplanes\.live|adsb\.fi", re.I),
    "something that looks like a real key": re.compile(r"FFQ_KEY=(?!paste-your-key-here)[A-Za-z0-9_-]{20,}"),
}
ALLOWED_EMAILS = {"noreply@flyonfreq.com"}


def tracked_files():
    """Every file git knows about AND every file it would pick up next (untracked, not ignored): nothing can hide from the scan by not being committed yet."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    files = [ROOT / f for f in out if f]
    return files if files else [p for p in ROOT.rglob("*") if p.is_file() and ".git/" not in str(p) and "__pycache__" not in str(p)]


def history_text():
    """Everything ever committed: authors, messages and every changed line. A name removed from a file is still in the history, and history is what gets published."""
    r = subprocess.run(["git", "log", "--all", "-p", "--format=%an %ae %cn %ce%n%B", "--", ".", ":(exclude)tools/check_repo.py"], cwd=ROOT, capture_output=True, text=True)   # this file lists the forbidden words, so it cannot be scanned for them
    return r.stdout if r.returncode == 0 else ""


def main():
    problems = []
    for path in tracked_files():
        if path.name == "check_repo.py" or path.suffix in (".png", ".jpg"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for what, rx in PATTERNS.items():
            for m in rx.finditer(text):
                if what == "an email address" and m.group(0).lower() in ALLOWED_EMAILS:
                    continue
                line = text[: m.start()].count("\n") + 1
                problems.append("%s:%d: %s (%s)" % (path.relative_to(ROOT), line, what, m.group(0)[:40]))
    hist = history_text()
    for what, rx in PATTERNS.items():
        for m in rx.finditer(hist):
            if what == "an email address" and m.group(0).lower() in ALLOWED_EMAILS:
                continue
            problems.append("git history: %s (%s)" % (what, m.group(0)[:40]))
            break
    if problems:
        print("NOT SAFE TO PUBLISH:\n  " + "\n  ".join(problems))
        return 1
    print("ok: no email, name, provider or key found in %d files" % len(tracked_files()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
