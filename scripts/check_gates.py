"""Quality-gates runner — the single source of truth for submission readiness.

Runs every mandatory gate from the submission guidelines in one command:
ruff (zero violations), pytest with coverage (fail_under handled by config),
file-length limit (<=150 code lines), hardcoded-value grep, and secrets grep.

Why a script and not memory: the final checklist (guidelines §17) must be
re-checkable at any moment with no human judgement involved.

Usage: uv run python scripts/check_gates.py [--skip-tests]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
# The 150-line limit covers the graded solution *and* its tests (guidelines
# §3.2 + §6.1 item 6). scripts/ is one-off tooling (e.g. the notebook
# generator, whose length is embedded cell content) and is out of scope.
LENGTH_SCOPED_DIRS = (SRC, ROOT / "tests")
MAX_CODE_LINES = 150

# Narrow on purpose: broad patterns drown real findings in false positives.
HARDCODE_PATTERNS = [
    (re.compile(r"[\"']https?://"), "URL literal (must come from config)"),
    (re.compile(r"api_key\s*=\s*[\"'][^\"']+[\"']"), "inline API key assignment"),
    (re.compile(r"\btimeout\s*=\s*\d"), "numeric timeout literal (use config)"),
    (re.compile(r"\brate_limit\s*=\s*\d"), "numeric rate limit literal (use config)"),
]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def count_code_lines(path: Path) -> int:
    """Count code lines: blank lines and comment-only lines are excluded."""
    total = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            total += 1
    return total


def check_file_lengths() -> list[str]:
    """Gate: solution + test files stay within MAX_CODE_LINES (§3.2, §6.1).

    Fixture trees under tests/fixtures/ vendor external sample repos verbatim,
    so they are exempt — they are data, not our code.
    """
    failures = []
    for base in LENGTH_SCOPED_DIRS:
        for path in sorted(base.rglob("*.py")):
            if "fixtures" in path.parts:
                continue
            lines = count_code_lines(path)
            if lines > MAX_CODE_LINES:
                failures.append(f"{path.relative_to(ROOT)}: {lines} code lines > {MAX_CODE_LINES}")
    return failures


def check_hardcodes() -> list[str]:
    """Gate: configurable values never live in src/ code (guidelines §7.2)."""
    failures = []
    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, reason in HARDCODE_PATTERNS:
                if pattern.search(line):
                    failures.append(f"{path.relative_to(ROOT)}:{lineno}: {reason}")
    return failures


def tracked_files() -> list[Path]:
    """All git-tracked files — the set that would ship in a submission zip."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [ROOT / name for name in out.stdout.splitlines()]


def check_secrets() -> list[str]:
    """Gate: no key-shaped strings anywhere in tracked files (guidelines §7.4)."""
    failures = []
    for path in tracked_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: matches {pattern.pattern}")
    return failures


def check_wikilinks() -> list[str]:
    """Gate (T201): every [[wikilink]] in vault/ resolves to an existing note."""
    vault = ROOT / "vault"
    if not vault.is_dir():
        return []
    stems = {p.stem for p in vault.rglob("*.md")}
    link = re.compile(r"\[\[([^\]|#]+)")
    failures = []
    for path in sorted(vault.rglob("*.md")):
        for target in link.findall(path.read_text(encoding="utf-8", errors="replace")):
            if target.strip() not in stems:
                failures.append(f"{path.relative_to(ROOT)}: broken link [[{target.strip()}]]")
    return failures


def run_tool(name: str, cmd: list[str]) -> bool:
    """Run an external gate (ruff/pytest); show output only on failure."""
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {name}")
        print(result.stdout[-3000:])
        print(result.stderr[-1000:])
        return False
    print(f"[ok]   {name}")
    return True


def main(argv: list[str]) -> int:
    """Run all gates; exit nonzero if any gate fails."""
    ok = True
    ok &= run_tool("ruff", ["uv", "run", "ruff", "check"])
    if "--skip-tests" not in argv:
        ok &= run_tool("pytest+coverage", ["uv", "run", "pytest", "-q"])
    for label, failures in [
        ("file-length<=150", check_file_lengths()),
        ("no-hardcodes", check_hardcodes()),
        ("no-secrets", check_secrets()),
        ("vault-wikilinks", check_wikilinks()),
    ]:
        if failures:
            ok = False
            print(f"[FAIL] {label}")
            for failure in failures:
                print(f"       {failure}")
        else:
            print(f"[ok]   {label}")
    print("GATES:", "GREEN" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
