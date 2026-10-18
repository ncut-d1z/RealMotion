"""Check the final latexmk log, beyond the compiler's exit status."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

PATTERNS = [r"^!", r"Undefined control sequence", r"Missing character:",
            r"LaTeX Error:", r"Package .+ Error:", r"Class .+ Error:",
            r"(?:Reference|Citation) .+ undefined", r"There were undefined (?:references|citations)",
            r"Label\(s\) may have changed", r"Rerun to get cross-references right",
            r"Overfull \\[hv]box"]


def issues(text: str) -> list[str]:
    return [line for line in text.splitlines() if any(re.search(p, line) for p in PATTERNS)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    found = issues(text)
    if not re.search(r"Output written on .+\.(?:pdf|xdv)", text):
        found.append("No successful output marker in compiler log")
    for line in found:
        print(line)
    if not found:
        print("LaTeX log passed: no errors, missing glyphs, undefined references or overfull boxes.")
    return int(bool(found))


if __name__ == "__main__":
    raise SystemExit(main())
