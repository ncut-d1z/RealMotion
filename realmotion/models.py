"""Vehicle mechanics. SI units; R maps body to world; body axes = forward/left/up.

Equations and validity conditions are derived in theory.tex. These are simulation
models, not a calibrated vehicle controller or a complete visual odometry system.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

Array = NDArray[np.float64]


def vector(value: ArrayLike, size: int = 3) -> Array:
    result = np.asarray(value, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"Expected a finite vector of shape ({size},)")
    return result


def positive(value: float, name: str) -> float:
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


def rotation_matrix(value: ArrayLike) -> Array:
    result = np.asarray(value, dtype=float)
    if (result.shape != (3, 3) or not np.isfinite(result).all()
            or not np.allclose(result.T @ result, np.eye(3), atol=1e-10, rtol=0)
            or not np.isclose(np.linalg.det(result), 1.0, atol=1e-10, rtol=0)):
        raise ValueError("Expected a proper rotation matrix")
    return result


def time_grid(times: ArrayLike) -> Array:
    t = np.asarray(times, dtype=float)
    if (t.ndim != 1 or len(t) < 2 or not np.isfinite(t).all()
            or t[0] != 0 or not np.all(np.diff(t) > 0)):
        raise ValueError("times must start at zero and be finite, strictly increasing")
    return t


def skew(value: ArrayLike) -> Array:
    x, y, z = vector(value)
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], dtype=float)


def rotz(angle: float) -> Array:
    if not np.isfinite(angle):
        raise ValueError("angle must be finite")
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def planar_arc(speed: float, yaw_rate: float, times: ArrayLike) -> Array:
    """Exact constant body-twist trajectory, including reverse and zero-yaw cases."""
    t = np.asarray(times, dtype=float)
    if (t.ndim != 1 or not np.isfinite(t).all()
            or not np.isfinite([speed, yaw_rate]).all()):
        raise ValueError("Non-finite or non-vector arc input")
    theta = yaw_rate * t
    x = speed * t * np.sinc(theta / np.pi)
    y = speed * t * theta / 2 * np.sinc(theta / (2 * np.pi)) ** 2
    return np.column_stack((x, y, theta))


def integrate_car(times: ArrayLike, speed: float, steering: Callable[[float], float],
                  wheelbase: float, rtol: float = 1e-9, atol: float = 1e-11) -> Array:
    """Rear-axle bicycle model. Steering is in radians; no lateral tire slip."""
    t = time_grid(times)
    length = positive(wheelbase, "wheelbase")
    positive(rtol, "rtol")
    positive(atol, "atol")
    if not np.isfinite(speed):
        raise ValueError("speed must be finite")

    def rhs(time: float, state: Array) -> Array:
        delta = float(steering(time))
        if not np.isfinite(delta) or abs(delta) >= np.pi / 2:
            raise ValueError("steering must be finite and strictly inside +/- pi/2")
        return np.array([speed * np.cos(state[2]), speed * np.sin(state[2]),
                         speed * np.tan(delta) / length])

    result = solve_ivp(rhs, (0, t[-1]), np.zeros(3), t_eval=t, method="DOP853",
                       rtol=rtol, atol=atol, max_step=float(np.min(np.diff(t))))
    if not result.success or not np.isfinite(result.y).all():
        raise RuntimeError(f"Car integration failed: {result.message}")
    return result.y.T


def ackermann_angles(delta: float, wheelbase: float, track: float) -> Array:
    """Front left/right steering angles; rear axle is the body reference point."""
    length, width = positive(wheelbase, "wheelbase"), positive(track, "track")
    if not np.isfinite(delta) or abs(delta) >= np.pi / 2:
        raise ValueError("Invalid equivalent steering angle")
    tangent = np.tan(delta)
    denominators = np.array([1 - width * tangent / (2 * length),
                             1 + width * tangent / (2 * length)])
    if np.min(denominators) <= 0:
        raise ValueError("Steering puts the ICR between the front wheels")
    return np.arctan2(tangent, denominators)


def lateral_wheel_residual(velocity: ArrayLike, yaw_rate: float,
                           positions: ArrayLike, steering: ArrayLike) -> Array:
    """Lateral contact velocity for each conventional wheel (not Mecanum)."""
    vel = vector(velocity, 2)
    xy, delta = np.asarray(positions, float), np.asarray(steering, float)
    if (xy.ndim != 2 or xy.shape[1] != 2 or delta.shape != (len(xy),)
            or not np.isfinite(xy).all() or not np.isfinite(delta).all()
            or not np.isfinite(yaw_rate)):
        raise ValueError("Invalid wheel positions, steering or yaw rate")
    contact = vel + yaw_rate * np.column_stack((-xy[:, 1], xy[:, 0]))
    normal = np.column_stack((-np.sin(delta), np.cos(delta)))
    return np.einsum("ni,ni->n", contact, normal)


def camera_delta(relative_body_rotation: ArrayLike, body_translation: ArrayLike,
                 camera_to_body: ArrayLike, lever_arm: ArrayLike) -> tuple[Array, Array]:
    """Finite motion: translations expressed in the FIRST body/camera frame."""
    rb = rotation_matrix(relative_body_rotation)
    rbc = rotation_matrix(camera_to_body)
    tb, lever = vector(body_translation), vector(lever_arm)
    return rbc.T @ rb @ rbc, rbc.T @ (tb + (rb - np.eye(3)) @ lever)


def camera_velocity(body_velocity: ArrayLike, body_rate: ArrayLike,
                    camera_to_body: ArrayLike, lever_arm: ArrayLike) -> Array:
    rbc = rotation_matrix(camera_to_body)
    return rbc.T @ (vector(body_velocity) + np.cross(vector(body_rate), vector(lever_arm)))


def velocity_constraint(rotation: ArrayLike, world_velocity: ArrayLike) -> tuple[Array, Array, Array]:
    """Rear axle h=[v_y^B,v_z^B]; right-local attitude Jacobian and world-v Jacobian."""
    r = rotation_matrix(rotation)
    local = r.T @ vector(world_velocity)
    return local[1:], skew(local)[1:, :], r.T[1:, :]


def allocation_matrix(arm: float, torque_thrust_ratio: float) -> Array:
    """Plus layout: rotors at +x,+y,-x,-y; reaction-z signs +,-,+,-."""
    arm = positive(arm, "arm")
    k = positive(torque_thrust_ratio, "torque_thrust_ratio")
    return np.array([[1, 1, 1, 1], [0, arm, 0, -arm],
                     [-arm, 0, arm, 0], [k, -k, k, -k]], dtype=float)


def simulate_quad(times: ArrayLike, rotation0: ArrayLike, velocity0: ArrayLike,
                  omega0: ArrayLike, rotor_forces: ArrayLike, *, mass: float,
                  inertia: ArrayLike, arm: float, torque_thrust_ratio: float,
                  rotor_max: float, gravity: float = 9.81, drag: float = 0.0,
                  rtol: float = 1e-9, atol: float = 1e-11) -> dict[str, Array]:
    """Integrate 6-DoF Newton-Euler dynamics with constant per-rotor thrusts.

    State = p_W, v_W, q_WB(x,y,z,w), omega_B. Linear isotropic drag is a
    deliberately simplified force -drag*v_W (kg/s); no motor lag, wind or ground.
    """
    t = time_grid(times)
    mass, gravity = positive(mass, "mass"), positive(gravity, "gravity")
    positive(rtol, "rtol")
    positive(atol, "atol")
    j = vector(inertia)
    forces = vector(rotor_forces, 4)
    if (np.any(j <= 0) or np.any(forces < 0)
            or np.any(forces > positive(rotor_max, "rotor_max"))
            or not np.isfinite(drag) or drag < 0):
        raise ValueError("Invalid inertia, drag or actuator bounds")
    # Principal moments must satisfy the rigid-body triangle inequalities.
    if np.max(j) > np.sum(j) - np.max(j) + 1e-12:
        raise ValueError("Principal inertias violate triangle inequalities")
    wrench = allocation_matrix(arm, torque_thrust_ratio) @ forces
    initial = np.r_[np.zeros(3), vector(velocity0),
                    Rotation.from_matrix(rotation_matrix(rotation0)).as_quat(), vector(omega0)]
    g = np.array([0.0, 0.0, -gravity])

    def rhs(_time: float, state: Array) -> Array:
        velocity, q, omega = state[3:6], state[6:10], state[10:13]
        r = Rotation.from_quat(q).as_matrix()
        acceleration = g + wrench[0] / mass * r[:, 2] - drag / mass * velocity
        qdot = 0.5 * np.r_[q[3] * omega + np.cross(q[:3], omega), -q[:3] @ omega]
        wdot = (wrench[1:] - np.cross(omega, j * omega)) / j
        return np.r_[velocity, acceleration, qdot, wdot]

    result = solve_ivp(rhs, (0, t[-1]), initial, t_eval=t, method="DOP853",
                       rtol=rtol, atol=atol, max_step=float(np.min(np.diff(t))))
    if not result.success or not np.isfinite(result.y).all():
        raise RuntimeError(f"Quadrotor integration failed: {result.message}")
    state = result.y.T
    rotations = Rotation.from_quat(state[:, 6:10]).as_matrix()
    acceleration = (g + wrench[0] / mass * rotations[:, :, 2]
                    - drag / mass * state[:, 3:6])
    return {"t": t, "position": state[:, :3], "velocity": state[:, 3:6],
            "rotation": rotations, "omega": state[:, 10:13], "acceleration": acceleration,
            "quaternion_norm_error": np.linalg.norm(state[:, 6:10], axis=1) - 1,
            "rotor_forces": forces}


def thrust_projection_scale(rotations: ArrayLike, visual_acceleration: ArrayLike,
                            world_gravity: ArrayLike) -> tuple[float, float]:
    """Conditional LS scale, assuming known gravity direction and drag-free model.

    Returns (positive scale, information). Rejects hovering/weak excitation;
    this is NOT a general statement that arbitrary monocular VO has metric scale.
    """
    rs = np.asarray(rotations, float)
    acc = np.asarray(visual_acceleration, float)
    g = vector(world_gravity)
    if (rs.ndim != 3 or rs.shape[1:] != (3, 3) or acc.shape != (len(rs), 3)
            or len(rs) == 0 or not np.isfinite(rs).all() or not np.isfinite(acc).all()):
        raise ValueError("Invalid scale-estimation arrays")
    for r in rs:
        rotation_matrix(r)
    b3 = rs[:, :, 2]
    a = acc - np.einsum("ni,ni->n", acc, b3)[:, None] * b3
    b = g - (b3 @ g)[:, None] * b3
    information = float(np.sum(a * a))
    if information < 1e-12:
        raise ValueError("Scale unobservable or numerically weak")
    scale = float(np.sum(a * b) / information)
    if scale <= 0 or not np.isfinite(scale):
        raise ValueError("Model inconsistent with positive scale")
    return scale, information
