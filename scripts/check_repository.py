"""Fail on tracked data/illustrations/binaries, including git add -f bypasses."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess

SOURCE_SUFFIXES = {".py", ".toml", ".tex", ".bib", ".md", ".yml", ".yaml"}
SOURCE_NAMES = {".gitignore", ".gitattributes", ".latexmkrc", "LICENSE", "requirements.txt", "requirements-dev.txt"}
BLOCKED_DIRS = {"outputs", "artifacts", "results", "data", "figures", "generated", "build",
                "dist", "__pycache__", ".venv", ".pytest_cache"}
IGNORE_PROBES = ["outputs/anything.weird", "test.npz", "nested/a.CsV", "plot.PNG", "plot.svg",
                 "theory.pdf", "dump.json", "nested/a.mcap", "test.npy", "measurements.h5"]


def allowed_path(name: str) -> bool:
    p = PurePosixPath(name)
    if any(part.lower() in BLOCKED_DIRS or part.startswith(".staging-") for part in p.parts):
        return False
    return p.name in SOURCE_NAMES or p.suffix in SOURCE_SUFFIXES


def check(root: Path, *, probe_ignores: bool = True) -> list[str]:
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
    errors = []
    for raw in tracked.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8")
        path = root/name
        if not allowed_path(name):
            errors.append(f"Tracked non-source/generated path: {name}")
            continue
        if path.is_symlink() or not path.is_file():
            errors.append(f"Tracked path is not a regular source file: {name}")
            continue
        content = path.read_bytes()
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"Non-UTF-8 source: {name}")
        if b"\0" in content:
            errors.append(f"Binary content in source path: {name}")
    if probe_ignores:
        for name in IGNORE_PROBES:
            code = subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", name], cwd=root).returncode
            if code != 0:
                errors.append(f"Missing .gitignore protection: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.root.resolve())
    for error in errors:
        print(error)
    if not errors:
        print("Repository policy passed: tracked files are UTF-8 sources/configuration only.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
