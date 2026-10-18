from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from realmotion.config import Config, load_config
from realmotion.experiments import prior_monte_carlo
from realmotion.runner import run

ROOT = Path(__file__).resolve().parents[1]


def compare_runs(first, second):
    m1 = json.loads((first/"manifest.json").read_text())
    m2 = json.loads((second/"manifest.json").read_text())
    assert m1["complete"] and m2["complete"]
    assert m1["experiments"] == m2["experiments"]
    assert m1["config_sha256"] == m2["config_sha256"]
    for path in first.glob("*.npz"):
        with np.load(path, allow_pickle=False) as a, np.load(second/path.name, allow_pickle=False) as b:
            assert a.files == b.files
            for key in a.files:
                np.testing.assert_array_equal(a[key], b[key])


def test_full_pipeline_reentry_and_all_plots(tmp_path):
    c = load_config(ROOT/"configs/smoke.toml")
    before = asdict(c)
    one = run(c, tmp_path, plots=True)
    two = run(c, tmp_path, plots=False)
    assert one != two and asdict(c) == before
    compare_runs(one, two)
    assert len(list(one.glob("*.npz"))) == 7
    assert len(list(one.glob("*.png"))) == 9
    from PIL import Image
    for path in one.glob("*.png"):
        with Image.open(path) as image:
            image.verify()
    assert not list(tmp_path.glob(".staging-*"))


def test_simultaneous_processes_same_output_root(tmp_path):
    command = [sys.executable, "-m", "realmotion", "--config", str(ROOT/"configs/smoke.toml"),
               "--output-root", str(tmp_path), "--experiments", "prior_monte_carlo", "--no-plots"]
    def launch(_):
        return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True, timeout=60)
    with ThreadPoolExecutor(max_workers=2) as executor:
        completed = list(executor.map(launch, range(2)))
    paths = [Path(value.stdout.strip()) for value in completed]
    assert paths[0] != paths[1]
    compare_runs(*paths)
    assert not list(tmp_path.glob(".staging-*"))


def test_order_does_not_change_random_stream(tmp_path):
    c = Config(duration_s=.2, sample_period_s=.1, trials=50)
    a = run(c, tmp_path, experiments=["car_circle", "prior_monte_carlo"], plots=False)
    b = run(c, tmp_path, experiments=["prior_monte_carlo", "car_circle"], plots=False)
    compare_runs(a, b)
    assert prior_monte_carlo(c).metrics == prior_monte_carlo(c).metrics


def test_failure_is_transactional(tmp_path, monkeypatch):
    import realmotion.runner as module
    c = Config(duration_s=.2, sample_period_s=.1, trials=50)
    good = run(c, tmp_path, experiments=["prior_monte_carlo"], plots=False)
    manifest = (good/"manifest.json").read_bytes()
    def fail(_):
        raise RuntimeError("injected failure")
    monkeypatch.setitem(module.EXPERIMENTS, "car_circle", fail)
    with pytest.raises(RuntimeError, match="injected"):
        run(c, tmp_path, experiments=["prior_monte_carlo", "car_circle"], plots=False)
    assert list(tmp_path.iterdir()) == [good]
    assert (good/"manifest.json").read_bytes() == manifest


@pytest.mark.parametrize("kwargs", [{"seed": True}, {"trials": 0}, {"mass_kg": -1},
                                   {"sample_period_s": 0}, {"steering_deg": 90},
                                   {"inertia_kgm2": [1, 1, 3]}, {"drag_kgps": -1},
                                   {"tilt_deg": float("nan")}, {"lever_arm_m": [1, 2]},
                                   {"duration_s": 1e8}, {"slip_degrees": []}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_unknown_toml_and_cli_exit(tmp_path):
    config = tmp_path/"bad.toml"
    config.write_text("typo = 1\n")
    with pytest.raises(ValueError, match="Unknown"):
        load_config(config)
    output = tmp_path/"output"
    process = subprocess.run([sys.executable, "-m", "realmotion", "--config", str(config),
                              "--output-root", str(output)], cwd=ROOT, capture_output=True, timeout=30)
    assert process.returncode == 2 and not output.exists()


def test_bad_selection_never_creates_output(tmp_path):
    for selection in ([], ["car_circle", "car_circle"], ["unknown"]):
        with pytest.raises(ValueError):
            run(Config(), tmp_path/"output", experiments=selection)
    assert not (tmp_path/"output").exists()
