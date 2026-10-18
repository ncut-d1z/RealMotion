"""Strict, immutable TOML configuration. Defaults are synthetic, not vendor fits."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
import tomllib

import numpy as np


@dataclass(frozen=True, slots=True)
class Config:
    seed: int = 20261018
    duration_s: float = 6.0
    sample_period_s: float = 0.02
    rtol: float = 1e-9
    atol: float = 1e-11
    wheelbase_m: float = 2.6
    track_m: float = 1.6
    speed_mps: float = 3.0
    steering_deg: float = 15.0
    steering_rate_degps: float = 4.0
    skid_axle_halfspan_m: float = 0.28
    skid_track_m: float = 0.55
    skid_effective_track_m: float = 0.715
    lever_arm_m: tuple[float, float, float] = (0.8, 0.15, 0.2)
    mass_kg: float = 1.0
    gravity_mps2: float = 9.81
    arm_m: float = 0.2
    inertia_kgm2: tuple[float, float, float] = (0.01, 0.01, 0.02)
    torque_thrust_ratio_m: float = 0.01
    rotor_max_n: float = 5.0
    tilt_deg: float = 15.0
    drag_kgps: float = 0.2
    yaw_rate_radps: float = 0.5
    scale_truth: float = 3.7
    trials: int = 20000
    observation_noise_deg: float = 2.0
    yaw_noise_deg: float = 0.5
    model_noise_deg: float = 0.5
    gate_sigma: float = 3.0
    slip_degrees: tuple[float, ...] = (0.0, 2.0, 5.0, 10.0)

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in {"lever_arm_m", "inertia_kgm2", "slip_degrees"}:
                if (not isinstance(value, (tuple, list)) or (len(value) != 3 if field.name != "slip_degrees" else not 1 <= len(value) <= 200)
                        or any(isinstance(v, bool) or not isinstance(v, (int, float))
                               or not np.isfinite(v) for v in value)):
                    raise ValueError(f"{field.name}: invalid finite-number vector")
                object.__setattr__(self, field.name, tuple(float(v) for v in value))
            elif field.name in {"seed", "trials"}:
                if type(value) is not int or value < (2 if field.name == "trials" else 0):
                    raise ValueError(f"{field.name}: invalid integer")
            elif (isinstance(value, bool) or not isinstance(value, (int, float))
                  or not np.isfinite(value)):
                raise ValueError(f"{field.name}: expected a finite number")
        signed = {"seed", "steering_deg", "steering_rate_degps", "speed_mps",
                  "yaw_rate_radps", "lever_arm_m", "inertia_kgm2", "slip_degrees", "tilt_deg", "drag_kgps"}
        for name, value in asdict(self).items():
            if name not in signed and value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.drag_kgps < 0:
            raise ValueError("drag_kgps must be non-negative")
        if not 0 < self.sample_period_s <= self.duration_s / 2:
            raise ValueError("Require 0 < sample_period_s <= duration_s/2")
        if self.duration_s / self.sample_period_s > 1_000_000 or self.trials > 2_000_000:
            raise ValueError("Configuration exceeds the documented in-memory safety limit")
        end_steer = self.steering_deg + self.steering_rate_degps * self.duration_s
        if max(abs(self.steering_deg), abs(end_steer), abs(self.tilt_deg)) >= 75:
            raise ValueError("Steering/tilt must remain below 75 degrees in these experiments")
        if self.speed_mps <= 0:
            raise ValueError("Experiments use forward motion; the models also support reverse")
        j = np.asarray(self.inertia_kgm2)
        if np.any(j <= 0) or np.max(j) > np.sum(j) - np.max(j) + 1e-12:
            raise ValueError("Invalid principal moments of inertia")
        if self.mass_kg * self.gravity_mps2 / np.cos(np.deg2rad(self.tilt_deg)) > 4 * self.rotor_max_n:
            raise ValueError("Insufficient rotor thrust for the selected tilted case")

    def times(self) -> np.ndarray:
        count = int(np.ceil(self.duration_s / self.sample_period_s))
        return np.linspace(0, self.duration_s, count + 1)


def load_config(path: str | Path) -> Config:
    with Path(path).open("rb") as stream:
        values = tomllib.load(stream)
    unknown = set(values) - {field.name for field in fields(Config)}
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    return Config(**values)
