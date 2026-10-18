from dataclasses import replace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from realmotion.config import Config
from realmotion.experiments import EXPERIMENTS, camera_extrinsic, quad_cases
from realmotion.models import (ackermann_angles, allocation_matrix, camera_delta,
                              camera_velocity, integrate_car, lateral_wheel_residual,
                              planar_arc, rotation_matrix, simulate_quad,
                              thrust_projection_scale, velocity_constraint)


@pytest.mark.parametrize("speed", [-2., 0., 2.])
@pytest.mark.parametrize("steer", [-0.3, 0., 1e-12, 0.3])
def test_car_against_independent_arc(speed, steer):
    times = np.linspace(0., 2., 31)
    numeric = integrate_car(times, speed, lambda _: steer, 2.6)
    exact = planar_arc(speed, speed*np.tan(steer)/2.6, times)
    np.testing.assert_allclose(numeric, exact, rtol=1e-10, atol=1e-11)


@pytest.mark.parametrize("delta", [-0.5, -0.1, 0., 0.1, 0.5])
def test_four_wheel_ackermann_contact_constraint(delta):
    length, width, speed = 2.6, 1.6, 3.
    xy = [[length, width/2], [length, -width/2], [0, width/2], [0, -width/2]]
    angles = np.r_[ackermann_angles(delta, length, width), 0., 0.]
    residual = lateral_wheel_residual([speed, 0.], speed*np.tan(delta)/length, xy, angles)
    np.testing.assert_allclose(residual, 0., atol=1e-14)


def test_camera_finite_pose_identity_arbitrary_3d():
    r0 = Rotation.from_rotvec([0.4, -0.2, 0.1]).as_matrix()
    r1 = Rotation.from_rotvec([-0.3, 0.7, -0.1]).as_matrix()
    rbc = Rotation.from_rotvec([0.1, 0.2, 0.3]).as_matrix()
    p0, p1, lever = np.array([1., 2., 3.]), np.array([-1., 0., 4.]), np.array([.8, -.2, .1])
    rc, tc = camera_delta(r0.T@r1, r0.T@(p1-p0), rbc, lever)
    np.testing.assert_allclose(rc, (r0@rbc).T@(r1@rbc), atol=1e-14)
    np.testing.assert_allclose(tc, (r0@rbc).T@(p1+r1@lever-p0-r0@lever), atol=1e-14)


def test_camera_velocity_and_acceleration_lever_arm():
    rbc, lever = camera_extrinsic(), np.array([.8, .15, .2])
    v, w, h = np.array([2., 0., 0.]), np.array([.2, -.1, .4]), 1e-4
    rplus, rminus = (Rotation.from_rotvec(sign*h*w).as_matrix() for sign in (1, -1))
    cp, cm, c0 = h*v+rplus@lever, -h*v+rminus@lever, lever
    np.testing.assert_allclose((cp-cm)/(2*h), rbc@camera_velocity(v, w, rbc, lever), atol=1e-8)
    np.testing.assert_allclose((cp-2*c0+cm)/h**2, np.cross(w, np.cross(w, lever)), atol=3e-8)


def test_right_local_jacobians_by_central_difference():
    r = Rotation.from_rotvec([.2, -.5, .1]).as_matrix()
    v, eps = np.array([1.5, .4, -.2]), 1e-6
    _, htheta, hv = velocity_constraint(r, v)
    for i in range(3):
        d = np.eye(3)[i]*eps
        plus = velocity_constraint(r@Rotation.from_rotvec(d).as_matrix(), v)[0]
        minus = velocity_constraint(r@Rotation.from_rotvec(-d).as_matrix(), v)[0]
        np.testing.assert_allclose((plus-minus)/(2*eps), htheta[:, i], atol=2e-10)
        plus = velocity_constraint(r, v+d)[0]
        minus = velocity_constraint(r, v-d)[0]
        np.testing.assert_allclose((plus-minus)/(2*eps), hv[:, i], atol=2e-10)


def test_quad_independent_closed_forms():
    c = Config(duration_s=1., sample_period_s=.05, trials=50)
    data, t = quad_cases(c), c.times()
    np.testing.assert_allclose(data["hover"]["position"], 0., atol=1e-12)
    np.testing.assert_allclose(data["yaw_hover"]["position"], 0., atol=1e-12)
    np.testing.assert_allclose(data["yaw_hover"]["omega"][:, 2], c.yaw_rate_radps*t/c.duration_s, atol=1e-12)
    np.testing.assert_allclose(data["sideways"]["position"][:, 1], c.speed_mps*t, atol=1e-12)
    acceleration = c.gravity_mps2*np.tan(np.deg2rad(c.tilt_deg))
    np.testing.assert_allclose(data["tilted"]["position"][:, 0], .5*acceleration*t**2, atol=1e-11)
    rate = c.drag_kgps/c.mass_kg
    expected_velocity = acceleration/rate*(-np.expm1(-rate*t))
    expected_position = acceleration/rate*(t+np.expm1(-rate*t)/rate)
    np.testing.assert_allclose(data["tilted_drag"]["velocity"][:, 0], expected_velocity, atol=1e-11)
    np.testing.assert_allclose(data["tilted_drag"]["position"][:, 0], expected_position, atol=1e-11)
    assert np.max(np.abs(data["yaw_hover"]["quaternion_norm_error"])) < 1e-10


def test_scale_conditional_and_degenerate():
    c = Config(duration_s=1., sample_period_s=.1, trials=50)
    result = EXPERIMENTS["scale_observability"](c)
    assert result.metrics["quad_known_gravity_scale"] == pytest.approx(c.scale_truth, abs=1e-12)
    assert result.metrics["car_max_scale_error"] < 1e-10
    assert result.metrics["quad_hover_rejected"] == 1.
    assert not result.arrays["car_valid"][0]
    lateral_only = EXPERIMENTS["scale_observability"](replace(c, lever_arm_m=(0., .2, .1)))
    assert lateral_only.metrics["car_valid_samples"] == 0
    with pytest.raises(ValueError, match="unobservable"):
        thrust_projection_scale(np.eye(3)[None], np.zeros((1, 3)), [0, 0, -9.81])


def test_skid_and_half_angle():
    c = Config(duration_s=1., sample_period_s=.05, trials=50)
    assert EXPERIMENTS["skid_steer"](c).metrics["no_slip_constraint_rank"] == 2.
    metrics = EXPERIMENTS["finite_chord"](c).metrics
    assert metrics["constant_curvature_max_rmse_deg"] < 1e-10
    assert metrics["varying_curvature_max_rmse_deg"] > .1


@pytest.mark.parametrize("matrix", [np.diag([1, 1, -1]), np.ones((3, 3)), np.full((3, 3), np.nan)])
def test_reject_non_rotations(matrix):
    with pytest.raises(ValueError):
        rotation_matrix(matrix)


@pytest.mark.parametrize("change", [{"mass": 0.}, {"rotor_max": 1.}, {"drag": -1.},
                                    {"inertia": [1., 1., 3.]}, {"arm": 0.}])
def test_quad_rejects_invalid_physics(change):
    options = dict(mass=1., inertia=[.01, .01, .02], arm=.2,
                   torque_thrust_ratio=.01, rotor_max=5.)
    options.update(change)
    with pytest.raises(ValueError):
        simulate_quad([0., .1], np.eye(3), [0, 0, 0], [0, 0, 0], [2.4525]*4, **options)


@pytest.mark.parametrize("times", [[1., 2.], [0., 0.], [0., np.nan], [0., -1.]])
def test_time_validation(times):
    with pytest.raises(ValueError):
        integrate_car(times, 1., lambda _: 0., 2.)


def test_allocation_signs_and_actuator_limits():
    a = allocation_matrix(.2, .01)
    np.testing.assert_allclose(a@np.ones(4), [4, 0, 0, 0], atol=1e-14)
    np.testing.assert_allclose(a@np.array([0, 1, 0, 0]), [1, .2, 0, -.01])
    with pytest.raises(ValueError):
        ackermann_angles(1.4, 1., 2.)


def test_finite_chord_rejects_nonlocal_arc():
    c = Config(duration_s=2., sample_period_s=.1, speed_mps=100., steering_rate_degps=0.)
    with pytest.raises(ValueError, match="short chords"):
        EXPERIMENTS["finite_chord"](c)
