import numpy as np
import pandas as pd
from lunalink.adcs import (
    aerodynamic_drag_torque,
    bdot_detumble_demo,
    box_inertia,
    gravity_gradient_torque,
    magnetic_torque,
    quaternion_normalize,
    rigid_body_omega_derivative,
    rigid_body_omega_step_rk4,
    run_adcs,
    solar_radiation_pressure_torque,
)


def test_box_inertia_matches_default_bus_dimensions():
    inertia = box_inertia()

    assert np.allclose(np.diag(inertia), [135.4167, 208.3333, 260.4167], atol=0.01)


def test_quaternion_normalize_returns_unit_quaternion():
    q = quaternion_normalize(np.array([2.0, -1.0, 0.5, 0.25]))

    assert np.isclose(np.linalg.norm(q), 1.0)


def test_gravity_gradient_torque_zero_when_principal_axis_aligned_with_radius():
    inertia = box_inertia()
    r_eci_m = np.array([7_000_000.0, 0.0, 0.0])

    torque = gravity_gradient_torque(inertia, r_eci_m)

    assert np.allclose(torque, np.zeros(3), atol=1e-15)


def test_magnetic_torque_is_perpendicular_to_field():
    magnetic_moment_a_m2 = np.array([250.0, -100.0, 50.0])
    magnetic_field_t = np.array([2.0e-5, -1.0e-5, 3.0e-5])

    torque = magnetic_torque(magnetic_moment_a_m2, magnetic_field_t)

    assert np.isclose(np.dot(torque, magnetic_field_t), 0.0, atol=1e-18)


def test_bdot_detumble_demo_reduces_angular_speed():
    history, summary = bdot_detumble_demo(duration_s=1800.0, step_s=1.0)

    assert len(history) > 2
    assert summary["final_angular_speed_deg_s"] < summary["initial_angular_speed_deg_s"]


def test_rigid_body_derivative_includes_gyroscopic_term():
    inertia = np.diag([2.0, 3.0, 4.0])
    omega = np.array([0.1, 0.2, 0.3])

    omega_dot = rigid_body_omega_derivative(inertia, omega, np.zeros(3))

    assert not np.allclose(omega_dot, np.zeros(3))


def test_rk4_omega_step_preserves_torque_free_principal_axis_spin():
    inertia = np.diag([2.0, 3.0, 4.0])
    omega = np.array([0.1, 0.0, 0.0])

    stepped = rigid_body_omega_step_rk4(inertia, omega, np.zeros(3), 100.0)

    assert np.allclose(stepped, omega)


def test_srp_and_drag_torques_zero_without_environment_loads():
    q = np.array([1.0, 0.0, 0.0, 0.0])

    srp = solar_radiation_pressure_torque(
        [1.0, 0.0, 0.0], q, 0.0, 2.0, 1.5, [0.1, 0.0, 0.0]
    )
    drag = aerodynamic_drag_torque(
        [7_000_000.0, 0.0, 0.0],
        [0.0, 7_500.0, 0.0],
        q,
        0.0,
        2.2,
        1.0,
        [0.1, 0.0, 0.0],
    )

    assert np.allclose(srp, np.zeros(3))
    assert np.allclose(drag, np.zeros(3))


def test_run_adcs_records_diagnostics_for_review():
    environment = pd.DataFrame(
        {
            "t_s": [0.0, 10.0],
            "x_eci_m": [7_000_000.0, 7_000_000.0],
            "y_eci_m": [0.0, 75_000.0],
            "z_eci_m": [0.0, 0.0],
            "vx_eci_mps": [0.0, 0.0],
            "vy_eci_mps": [7_500.0, 7_500.0],
            "vz_eci_mps": [0.0, 0.0],
            "sun_hat_x": [1.0, 1.0],
            "sun_hat_y": [0.0, 0.0],
            "sun_hat_z": [0.0, 0.0],
            "solar_flux_w_m2": [1361.0, 1361.0],
            "b_eci_x_t": [0.0, 0.0],
            "b_eci_y_t": [0.0, 0.0],
            "b_eci_z_t": [3.0e-5, 3.0e-5],
            "atmospheric_density_kg_m3": [1.0e-12, 1.0e-12],
        }
    )

    history, summary = run_adcs(environment)

    assert history["q_norm"].between(0.999, 1.001).all()
    assert "max_total_torque_nm" in summary
    assert "wheel_model_scope" in summary
