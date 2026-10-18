"""Transactional experiment runner: private staging, unique output, no shared RNG."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
from threading import Lock
from typing import Sequence
from uuid import uuid4

import numpy as np

from .config import Config, load_config
from .experiments import EXPERIMENTS, Plot

_RENDER_LOCK = Lock()  # Matplotlib font/render internals are not thread-safe.


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_fingerprint() -> dict[str, str]:
    """Hash the actual working sources, not just a possibly stale Git commit."""
    root = Path(__file__).resolve().parents[1]
    paths = list((root / "realmotion").glob("*.py"))
    paths += list((root / "configs").glob("*.toml"))
    paths += [root / name for name in ("requirements.txt", "requirements-dev.txt", "theory.tex")]
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths) if p.is_file()}


def render(plot: Plot, path: Path) -> None:
    # Object-oriented Agg avoids pyplot's global current figure and any GUI backend.
    with _RENDER_LOCK:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        fig = Figure(figsize=(8, 5), layout="constrained")
        FigureCanvasAgg(fig)
        try:
            ax = fig.add_subplot()
            for label, x, y in plot.lines:
                ax.plot(x, y, label=label)
            ax.set(xlabel=plot.xlabel, ylabel=plot.ylabel, title=plot.title)
            if plot.equal:
                ax.set_aspect("equal", adjustable="datalim")
            if plot.logy:
                ax.set_yscale("log")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize="small")
            fig.savefig(path, dpi=150)
        finally:
            fig.clear()


def run(config: Config, output_root: str | Path, *,
        experiments: Sequence[str] | None = None, plots: bool = True) -> Path:
    """Return a new, complete run directory; never overwrite a previous run.

    Repeated calls and simultaneous processes use distinct staging/run directories.
    On failure only this invocation's staging directory is removed. A process kill
    may leave a hidden .staging-* directory, never a falsely complete run directory.
    Numerical reproducibility means equal arrays, not byte-identical ZIP/PNG files.
    """
    names = tuple(EXPERIMENTS) if experiments is None else tuple(experiments)
    if not names or len(set(names)) != len(names) or any(n not in EXPERIMENTS for n in names):
        raise ValueError("Select a nonempty, duplicate-free list of known experiments")
    resolved = asdict(config)
    config_hash = sha256(json.dumps(resolved, sort_keys=True, allow_nan=False).encode()).hexdigest()
    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    destination = root / f"run-{config_hash[:12]}-{uuid4().hex}"
    try:
        manifest = {
            "schema_version": 1, "complete": True, "config": resolved,
            "config_sha256": config_hash, "sources_sha256": source_fingerprint(),
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": {n: importlib.metadata.version(n) for n in ("numpy", "scipy", "matplotlib")},
            "experiments": {},
            "reproducibility": "Numeric arrays in the same environment; containers have metadata.",
            "truth_policy": "Synthetic SI ground truth is for simulation/evaluation, not a VO input.",
        }
        for name in names:
            result = EXPERIMENTS[name](config)
            arrays = {key: np.asarray(value) for key, value in result.arrays.items()}
            for key, array in arrays.items():
                if array.dtype.kind not in "biufc" or not np.isfinite(array).all():
                    raise ValueError(f"{name}/{key}: array must be finite numeric, not object")
            metrics = {key: float(value) for key, value in result.metrics.items()}
            if not np.isfinite(list(metrics.values())).all():
                raise ValueError(f"{name}: non-finite metrics")
            np.savez_compressed(stage / f"{name}.npz", **arrays)
            if plots:
                for plot in result.plots:
                    render(plot, stage / f"{plot.name}.png")
            manifest["experiments"][name] = {
                "metrics": metrics,
                "arrays": {key: {"shape": list(a.shape), "dtype": str(a.dtype),
                                 "sha256": sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}
                           for key, a in arrays.items()},
            }
        manifest["files_sha256"] = {p.name: digest(p) for p in sorted(stage.iterdir()) if p.is_file()}
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8")
        # Same-filesystem directory rename is the publication boundary, not fsync durability.
        os.replace(stage, destination)
        return destination
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs"))
    parser.add_argument("--experiments", nargs="+", choices=tuple(EXPERIMENTS))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(load_config(args.config), args.output_root,
                     experiments=args.experiments, plots=not args.no_plots)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Experiment failed: {exc}\n")
    print(output)
    return 0
