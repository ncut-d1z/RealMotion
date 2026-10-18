#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

command -v python3 >/dev/null 2>&1 || { echo "Python 3.13+ (python3) is required" >&2; exit 1; }
command -v latexmk >/dev/null 2>&1 || { echo "latexmk is missing; install texlive-xetex texlive-lang-chinese texlive-fonts-recommended latexmk" >&2; exit 1; }
command -v xelatex >/dev/null 2>&1 || { echo "xelatex is missing" >&2; exit 1; }
command -v kpsewhich >/dev/null 2>&1 || { echo "kpsewhich is missing" >&2; exit 1; }
for font in pzdr.tfm FandolSong-Regular.otf; do
    kpsewhich "$font" >/dev/null || { echo "Missing TeX font: $font" >&2; exit 1; }
done

if [[ ! -f .venv/pyvenv.cfg ]]; then
    python3 -m venv .venv
fi
if [[ -x .venv/bin/python ]]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    echo "Invalid .venv; remove or repair it manually" >&2
    exit 1
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 13), "Python 3.13+ required"'
export MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

echo "[1/7] Install development dependencies"
"$PYTHON" -m pip install -r requirements-dev.txt
echo "[2/7] Check source-only repository policy (when Git is available)"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    "$PYTHON" scripts/check_repository.py
else
    echo "Git checkout unavailable; repository policy check skipped"
fi
echo "[3/7] Compile Python sources"
"$PYTHON" -m compileall -q realmotion scripts tests
echo "[4/7] Run tests"
"$PYTHON" -m pytest -q
echo "[5/7] Smoke experiments"
"$PYTHON" -m realmotion --config configs/smoke.toml
echo "[6/7] Full experiments"
"$PYTHON" -m realmotion --config configs/default.toml
echo "[7/7] Compile and verify Chinese LaTeX"
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error theory.tex
"$PYTHON" scripts/check_latex_log.py build/theory.log
echo "Done. PDF: build/theory.pdf ; experiments: outputs/"
