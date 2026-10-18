"""Seven independent experiments; no output files or global RNG in this module."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable

import numpy as np
from scipy.spatial.transform import Rotation

from .config import Config
from .models import (ackermann_angles, allocation_matrix, camera_delta,
                     camera_velocity, integrate_car, lateral_wheel_residual,
                     planar_arc, rotz, simulate_quad, thrust_projection_scale)


@dataclass
class Plot:
    name: str
    xlabel: str
    ylabel: str
    lines: list[tuple[str, np.ndarray, np.ndarray]]
    title: str
    equal: bool = False
    logy: bool = False


@dataclass
class Result:
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    plots: list[Plot] = field(default_factory=list)


def rms(value: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(value) ** 2)))


def wrap(value: np.ndarray) -> np.ndarray:
    return np.arctan2(np.sin(value), np.cos(value))


def camera_extrinsic() -> np.ndarray:
    # Optical camera axes = right/down/forward; body = forward/left/up.
    return np.array([[0., 0., 1.], [-1., 0., 0.], [0., -1., 0.]])


def car_circle(c: Config) -> Result:
    t = c.times()
    arrays, lines, errors = {"time_s": t}, [], []
    for i, delta_deg in enumerate((-abs(c.steering_deg), 0., abs(c.steering_deg))):
        delta = np.deg2rad(delta_deg)
        rate = c.speed_mps * np.tan(delta) / c.wheelbase_m
        exact = planar_arc(c.speed_mps, rate, t)
        numeric = integrate_car(t, c.speed_mps, lambda _: delta, c.wheelbase_m, c.rtol, c.atol)
        arrays[f"exact_{i}"] = exact
        arrays[f"numeric_{i}"] = numeric
        errors.append(float(np.max(np.linalg.norm(exact[:, :2] - numeric[:, :2], axis=1))))
        lines.append((f"{delta_deg:g} deg (ODE)", numeric[:, 0], numeric[:, 1]))
    delta = np.deg2rad(c.steering_deg)
    angles = np.r_[ackermann_angles(delta, c.wheelbase_m, c.track_m), 0., 0.]
    xy = np.array([[c.wheelbase_m, c.track_m/2], [c.wheelbase_m, -c.track_m/2],
                   [0., c.track_m/2], [0., -c.track_m/2]])
    residual = lateral_wheel_residual([c.speed_mps, 0], c.speed_mps*np.tan(delta)/c.wheelbase_m,
                                      xy, angles)
    arrays.update(wheel_positions_m=xy, steering_angles_rad=angles,
                  wheel_lateral_velocity_mps=residual)
    return Result(arrays, {"max_position_error_m": max(errors),
                           "max_wheel_lateral_residual_mps": float(np.max(np.abs(residual)))},
                  [Plot("car_circle", "world x [m]", "world y [m]", lines,
                        "E01: rear-axle Ackermann trajectories", equal=True)])


def finite_chord(c: Config) -> Result:
    t = c.times()
    delta = np.deg2rad(c.steering_deg)
    fixed = integrate_car(t, c.speed_mps, lambda _: delta, c.wheelbase_m, c.rtol, c.atol)
    varying = integrate_car(t, c.speed_mps,
                            lambda time: delta + np.deg2rad(c.steering_rate_degps)*time,
                            c.wheelbase_m, c.rtol, c.atol)
    strides = sorted({n for n in (1, 2, 5, 10, 20) if n < len(t)})
    steps, constant_errors, varying_errors, tangent_errors = [], [], [], []
    for stride in strides:
        steps.append(t[stride])
        for trajectory, target in ((fixed, constant_errors), (varying, varying_errors)):
            change = trajectory[stride:, :2] - trajectory[:-stride, :2]
            phi = wrap(np.arctan2(change[:, 1], change[:, 0]) - trajectory[:-stride, 2])
            theta = trajectory[stride:, 2] - trajectory[:-stride, 2]
            if np.any(np.abs(theta) >= np.pi) or np.any(np.linalg.norm(change, axis=1) < 1e-12):
                raise ValueError("E02 requires nonzero short chords with frame yaw below pi")
            target.append(np.rad2deg(rms(wrap(phi - theta/2))))
            if trajectory is fixed:
                tangent_errors.append(np.rad2deg(rms(phi)))
    arrays = {"step_s": np.array(steps), "constant_rmse_deg": np.array(constant_errors),
              "varying_rmse_deg": np.array(varying_errors), "tangent_rmse_deg": np.array(tangent_errors)}
    lines = [("constant curvature: chord minus half-yaw", arrays["step_s"], arrays["constant_rmse_deg"]),
             ("varying curvature: chord minus half-yaw", arrays["step_s"], arrays["varying_rmse_deg"]),
             ("wrong prior: chord equals initial heading", arrays["step_s"], arrays["tangent_rmse_deg"])]
    return Result(arrays, {"constant_curvature_max_rmse_deg": max(constant_errors),
                           "varying_curvature_max_rmse_deg": max(varying_errors),
                           "initial_heading_max_rmse_deg": max(tangent_errors)},
                  [Plot("finite_chord", "frame interval [s]", "direction RMSE [deg]", lines,
                        "E02: instantaneous constraints are not finite chords")])


def skid_steer(c: Config) -> Result:
    a, width = c.skid_axle_halfspan_m, c.skid_track_m
    xy = np.array([[a, width/2], [a, -width/2], [-a, width/2], [-a, -width/2]])
    rates = np.linspace(-1., 1., 101)
    lateral = np.array([lateral_wheel_residual([1., 0.], r, xy, np.zeros(4)) for r in rates])
    constraint = np.column_stack((np.zeros(4), np.ones(4), xy[:, 0]))
    actual_rate = width / c.skid_effective_track_m * rates
    arrays = {"requested_yaw_rate_radps": rates, "contact_lateral_velocity_mps": lateral,
              "effective_yaw_rate_radps": actual_rate, "constraint_matrix": constraint}
    return Result(arrays, {"no_slip_constraint_rank": float(np.linalg.matrix_rank(constraint)),
                           "max_required_contact_slip_mps": float(np.max(np.abs(lateral))),
                           "max_effective_yaw_error_radps": float(np.max(np.abs(actual_rate-rates)))},
                  [Plot("skid_steer", "yaw rate [rad/s]", "contact lateral velocity [m/s]",
                        [("front wheel", rates, lateral[:, 0]), ("rear wheel", rates, lateral[:, 2])],
                        "E03: four fixed wheels need lateral slip to turn")])


def lever_arm(c: Config) -> Result:
    t, rbc = c.times(), camera_extrinsic()
    rate = c.speed_mps * np.tan(np.deg2rad(c.steering_deg)) / c.wheelbase_m
    body = planar_arc(c.speed_mps, rate, t)
    rotations = Rotation.from_euler("z", body[:, 2:3]).as_matrix()
    positions = np.column_stack((body[:, :2], np.zeros(len(t))))
    camera = positions + np.einsum("nij,j->ni", rotations, np.array(c.lever_arm_m))
    predicted = np.array([camera_delta(r, p, rbc, c.lever_arm_m)[1]
                          for r, p in zip(rotations, positions, strict=True)])
    observed = (camera-camera[0]) @ rbc
    ignored_error = np.linalg.norm(camera-camera[0]-positions, axis=1)
    pure_angle = c.yaw_rate_radps * (t[1]-t[0])
    _, pure_t = camera_delta(rotz(pure_angle), np.zeros(3), rbc, c.lever_arm_m)
    vel_c = camera_velocity([c.speed_mps, 0, 0], [0, 0, rate], rbc, c.lever_arm_m)
    arrays = {"time_s": t, "body_position_m": positions, "camera_position_m": camera,
              "camera_translation_in_first_camera_m": observed, "ignored_error_m": ignored_error,
              "camera_to_body": rbc, "camera_velocity_mps": vel_c}
    return Result(arrays, {"extrinsic_identity_max_error_m": float(np.max(np.abs(predicted-observed))),
                           "max_ignored_lever_error_m": float(np.max(ignored_error)),
                           "camera_lateral_body_axes_mps": float((rbc @ vel_c)[1]),
                           "pure_yaw_camera_displacement_m": float(np.linalg.norm(pure_t))},
                  [Plot("lever_arm", "world x [m]", "world y [m]",
                        [("rear axle", positions[:, 0], positions[:, 1]),
                         ("camera optical center", camera[:, 0], camera[:, 1])],
                        "E04: rigid camera lever-arm effect", equal=True)])


def quad_cases(c: Config) -> dict[str, dict[str, np.ndarray]]:
    t = c.times()
    mg = c.mass_kg*c.gravity_mps2
    matrix = allocation_matrix(c.arm_m, c.torque_thrust_ratio_m)
    yaw_torque = c.inertia_kgm2[2] * c.yaw_rate_radps / c.duration_s
    yaw_forces = np.linalg.solve(matrix, [mg, 0., 0., yaw_torque])
    tilted_forces = np.full(4, mg/(4*np.cos(np.deg2rad(c.tilt_deg))))
    tilted = Rotation.from_euler("y", c.tilt_deg, degrees=True).as_matrix()
    specs = {"hover": (np.eye(3), [0., 0., 0.], np.full(4, mg/4), 0.),
             "yaw_hover": (np.eye(3), [0., 0., 0.], yaw_forces, 0.),
             "sideways": (np.eye(3), [0., c.speed_mps, 0.], np.full(4, mg/4), 0.),
             "yaw_sideways": (np.eye(3), [0., c.speed_mps, 0.], yaw_forces, 0.),
             "tilted": (tilted, [0., 0., 0.], tilted_forces, 0.),
             "tilted_drag": (tilted, [0., 0., 0.], tilted_forces, c.drag_kgps)}
    result = {}
    for name, (rotation, velocity, forces, drag) in specs.items():
        result[name] = simulate_quad(t, rotation, velocity, np.zeros(3), forces,
                                    mass=c.mass_kg, inertia=c.inertia_kgm2, arm=c.arm_m,
                                    torque_thrust_ratio=c.torque_thrust_ratio_m,
                                    rotor_max=c.rotor_max_n, gravity=c.gravity_mps2, drag=drag,
                                    rtol=c.rtol, atol=c.atol)
    return result


def quadrotor(c: Config) -> Result:
    cases = quad_cases(c)
    arrays, finite_errors, ideal_residuals = {}, [], []
    for name, data in cases.items():
        arrays.update({f"{name}_{key}": value for key, value in data.items()})
        fd = np.gradient(data["velocity"], data["t"], axis=0, edge_order=2)
        finite_errors.append(float(np.max(np.linalg.norm(fd[1:-1]-data["acceleration"][1:-1], axis=1))))
        specific = data["acceleration"] + np.array([0., 0., c.gravity_mps2])
        local = np.einsum("nji,nj->ni", data["rotation"], specific)
        residual = np.linalg.norm(local[:, :2], axis=1)
        arrays[f"{name}_thrust_projection_residual_mps2"] = residual
        if name != "tilted_drag":
            ideal_residuals.append(float(np.max(residual)))
    drag_data = cases["tilted_drag"]
    corrected = drag_data["acceleration"] + [0., 0., c.gravity_mps2] + c.drag_kgps/c.mass_kg*drag_data["velocity"]
    corrected = np.einsum("nji,nj->ni", drag_data["rotation"], corrected)[:, :2]
    metrics = {"yaw_hover_max_position_m": float(np.max(np.linalg.norm(cases["yaw_hover"]["position"], axis=1))),
               "yaw_hover_final_body_rate_radps": float(cases["yaw_hover"]["omega"][-1, 2]),
               "sideways_final_displacement_m": float(cases["sideways"]["position"][-1, 1]),
               "ideal_projection_max_residual_mps2": max(ideal_residuals),
               "drag_ignored_max_residual_mps2": float(np.max(arrays["tilted_drag_thrust_projection_residual_mps2"])),
               "drag_corrected_max_residual_mps2": float(np.max(np.abs(corrected))),
               "interior_fd_acceleration_max_error_mps2": max(finite_errors),
               "quaternion_norm_max_error": max(float(np.max(np.abs(d["quaternion_norm_error"]))) for d in cases.values())}
    trajectory = [(name, d["position"][:, 0], d["position"][:, 1]) for name, d in cases.items()]
    residual_lines = [("drag-free", cases["tilted"]["t"], arrays["tilted_thrust_projection_residual_mps2"]),
                      ("drag present but ignored", drag_data["t"], arrays["tilted_drag_thrust_projection_residual_mps2"]),
                      ("drag compensated", drag_data["t"], np.linalg.norm(corrected, axis=1))]
    return Result(arrays, metrics,
                  [Plot("quad_trajectories", "world x [m]", "world y [m]", trajectory,
                        "E05: heading does not determine flight direction", equal=True),
                   Plot("quad_constraint", "time [s]", "transverse specific acceleration [m/s^2]",
                        residual_lines, "E05: thrust-axis constraint and model mismatch")])


def scale_observability(c: Config) -> Result:
    rbc = camera_extrinsic()
    theta = np.r_[0., np.geomspace(1e-7, 0.5, 80)]
    alpha, beta, estimated, valid = np.zeros((4, len(theta)))
    for i, angle in enumerate(theta):
        # Fix a 1 m forward arc length; this is an algebraic observability test.
        arc = planar_arc(1., angle, [1.])[0]
        translation = np.r_[arc[:2], 0.]
        rotation = rotz(angle)
        _, tc = camera_delta(rotation, translation, rbc, c.lever_arm_m)
        n = np.array([-np.sin(angle/2), np.cos(angle/2), 0.])
        alpha[i] = n @ rbc @ (tc/c.scale_truth)
        beta[i] = n @ (rotation-np.eye(3)) @ np.array(c.lever_arm_m)
        if abs(alpha[i]) > 1e-12:
            estimated[i], valid[i] = beta[i]/alpha[i], 1.
    cases = quad_cases(c)
    g = np.array([0., 0., -c.gravity_mps2])
    ideal = cases["tilted"]
    scale, information = thrust_projection_scale(ideal["rotation"], ideal["acceleration"]/c.scale_truth, g)
    drag = cases["tilted_drag"]
    wrong_scale, _ = thrust_projection_scale(drag["rotation"], drag["acceleration"]/c.scale_truth, g)
    candidates = np.linspace(0.2*c.scale_truth, 2*c.scale_truth, 101)
    abar = ideal["acceleration"]/c.scale_truth
    b3 = ideal["rotation"][:, :, 2]
    costs = []
    for candidate in candidates:
        residual = candidate*abar-g
        residual -= np.einsum("ni,ni->n", residual, b3)[:, None]*b3
        costs.append(float(np.mean(np.sum(residual**2, axis=1))))
    hover_rejected = 0.
    try:
        thrust_projection_scale(cases["hover"]["rotation"], cases["hover"]["acceleration"], g)
    except ValueError:
        hover_rejected = 1.
    mask = valid.astype(bool)
    arrays = {"yaw_rad": theta, "car_scale_alpha": alpha, "car_scale_beta": beta,
              "car_scale": estimated, "car_valid": mask, "candidate_scale": candidates,
              "quad_cost_m2ps4": np.array(costs)}
    metrics = {"car_valid_samples": float(np.count_nonzero(mask)),
               "car_max_scale_error": float(np.max(np.abs(estimated[mask]-c.scale_truth))) if mask.any() else 0.,
               "quad_known_gravity_scale": scale, "quad_information": information,
               "quad_drag_mismatched_scale": wrong_scale, "quad_hover_rejected": hover_rejected}
    return Result(arrays, metrics,
                  [Plot("car_scale_excitation", "frame yaw [rad]", "|scale coefficient| [visual units]",
                        [("known forward lever arm", theta, np.maximum(np.abs(alpha), 1e-18))],
                        "E06: scale degenerates as turning excitation vanishes", logy=True),
                   Plot("quad_scale_cost", "candidate metric scale", "mean squared residual [m^2/s^4]",
                        [("known gravity + ideal thrust model", candidates, np.array(costs))],
                        "E06: conditional scale information, not generic monocular scale")])


def prior_monte_carlo(c: Config) -> Result:
    rng = np.random.default_rng(np.random.SeedSequence([c.seed, 7]))
    obs_sd, yaw_sd, model_sd = np.deg2rad([c.observation_noise_deg, c.yaw_noise_deg, c.model_noise_deg])
    prior_variance = (yaw_sd/2)**2+model_sd**2
    innovation_sd = np.sqrt(obs_sd**2+prior_variance)
    weight = obs_sd**2/innovation_sd**2
    slips = np.array(c.slip_degrees)
    errors, biases, rejection = [], [], []
    for slip in np.deg2rad(slips):
        theta = 0.05  # Frame yaw, rad; chosen away from angle wrapping boundaries.
        truth = theta/2+slip
        raw = truth+rng.normal(0., obs_sd, c.trials)
        prior = theta/2+rng.normal(0., yaw_sd/2, c.trials)
        difference = wrap(prior-raw)
        soft = raw+weight*difference
        accepted = np.abs(difference) <= c.gate_sigma*innovation_sd
        gated = np.where(accepted, soft, raw)
        sample_errors = np.array([wrap(value-truth) for value in (raw, prior, soft, gated)])
        errors.append(np.rad2deg(np.sqrt(np.mean(sample_errors**2, axis=1))))
        biases.append(np.rad2deg(np.mean(sample_errors, axis=1)))
        rejection.append(1.-np.mean(accepted))
    rmse, bias = np.array(errors), np.array(biases)
    arrays = {"slip_degrees": slips, "rmse_degrees": rmse, "bias_degrees": bias,
              "gate_rejection_fraction": np.array(rejection)}
    names = ("raw observation", "hard prior", "soft prior", "innovation-gated prior")
    metrics = {f"slip_{i}_{name}_rmse_deg": float(rmse[i, j])
               for i in range(len(slips)) for j, name in enumerate(("raw", "hard", "soft", "gated"))}
    return Result(arrays, metrics,
                  [Plot("prior_monte_carlo", "systematic lateral slip [deg]", "direction RMSE [deg]",
                        [(name, slips, rmse[:, i]) for i, name in enumerate(names)],
                        "E07: prior benefit versus model-mismatch bias")])


EXPERIMENTS: dict[str, Callable[[Config], Result]] = {
    "car_circle": car_circle, "finite_chord": finite_chord, "skid_steer": skid_steer,
    "lever_arm": lever_arm, "quadrotor": quadrotor,
    "scale_observability": scale_observability, "prior_monte_carlo": prior_monte_carlo,
}
