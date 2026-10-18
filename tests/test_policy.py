from pathlib import Path
import subprocess

import pytest

from scripts.check_latex_log import issues
from scripts.check_repository import allowed_path, check


@pytest.mark.parametrize("path", ["a.NPZ", "a.csv", "a.PDF", "a.SVG", "data/hide.py",
                                  "x.json", "x.exe", "x.unknown", "build/theory.tex"])
def test_forbidden_paths(path):
    assert not allowed_path(path)


@pytest.mark.parametrize("path", ["theory.tex", "references.md", "realmotion/models.py",
                                  "configs/default.toml", ".github/workflows/ci.yml", "requirements.txt"])
def test_source_paths(path):
    assert allowed_path(path)


def test_forced_add_cannot_bypass_guard(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path/".gitignore").write_text("*.npz\n")
    (tmp_path/"bad.npz").write_bytes(b"binary\0data")
    subprocess.run(["git", "add", "-f", "bad.npz"], cwd=tmp_path, check=True)
    assert any("bad.npz" in e for e in check(tmp_path, probe_ignores=False))


@pytest.mark.parametrize("line", ["! Undefined control sequence.", "Missing character: no 字",
                                  "LaTeX Warning: Reference `x' on page 1 undefined.",
                                  "Overfull \\hbox (10.0pt too wide)",
                                  "LaTeX Warning: There were undefined references."])
def test_bad_latex_log(line):
    assert issues(line)


def test_clean_latex_log():
    assert not issues("Output written on theory.pdf (10 pages).")


def test_runner_context_not_used_in_job_level_env():
    # GitHub job-level env is evaluated before a runner exists.
    # This regression check is not a replacement for a complete Actions linter.
    import re
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text()
    for block in re.findall(r"(?m)^    env:\n((?:      .*\n)+)", workflow):
        assert "runner." not in block
    assert 'MPLCONFIGDIR=${RUNNER_TEMP}/matplotlib' in workflow
