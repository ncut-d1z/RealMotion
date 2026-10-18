from pathlib import Path
import re

from scripts.check_repository import allowed_path


def test_root_launchers_whitelisted_only():
    assert allowed_path("run.sh")
    assert allowed_path("run.ps1")
    assert not allowed_path("nested/run.ps1")
    assert not allowed_path("something-else.ps1")


def test_launchers_contain_full_pipeline_and_fail_fast():
    root = Path(__file__).resolve().parents[1]
    shell = (root / "run.sh").read_text(encoding="utf-8")
    powershell = (root / "run.ps1").read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in shell
    assert "$LASTEXITCODE" in powershell
    for token in (
        "requirements-dev.txt", "scripts/check_repository.py", "compileall",
        "pytest", "configs/smoke.toml", "configs/default.toml",
        "latexmk", "scripts/check_latex_log.py", "build/theory.log",
    ):
        assert token in shell
        assert token in powershell
    assert ".venv" in shell and ".venv" in powershell
    assert "python -m pip install" not in shell  # never use uncontrolled global Python


def test_no_generated_files_under_version_control():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "outputs").is_file()
