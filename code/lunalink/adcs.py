"""Simple attitude dynamics and control utilities for LunaLink."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .config import MissionConfig, default_mission_config
from .constants import (
    DEG2RAD,
    EARTH_EQUATORIAL_B_T,
    EARTH_MU_M3_S2,
    EARTH_RADIUS_M,
    EARTH_ROT_RATE_RAD_S,
    RAD2DEG,
    SPEED_OF_LIGHT_M_S,
)

Array3 = NDArray[np.float64]
Array4 = NDArray[np.float64]


@dataclass(frozen=True)
class AdcsConfig:
    """ADCS sizing defaults from the LunaLink execution plan."""

    initial_tumble_rad_s: float = 10.0 * DEG2RAD
    magnetorquer_max_dipole_a_m2: float = 400.0
    wheel_momentum_capacity_nms: float = 12.0
    bdot_gain_a_m2_per_t_s: float = 8.0e7
    magnetic_damping_nms: float = 0.03
    max_internal_step_s: float = 1.0
    wheel_desat_threshold_fraction: float = 0.75
    srp_reflectivity_coefficient: float = 1.5
    srp_area_m2: float = 2.0
    srp_center_of_pressure_body_m: tuple[float, float, float] = (0.02, -0.015, 0.01)
    drag_coefficient: float = 2.2
    drag_area_m2: float = 1.5
    drag_center_of_pressure_body_m: tuple[float, float, float] = (-0.03, 0.0, 0.015)
    residual_dipole_body_a_m2: tuple[float, float, float] = (0.2, -0.1, 0.05)


def _as_float_array(values: Any, expected_size: int) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=float)
    if array.size != expected_size:
        raise ValueError(f"Expected {expected_size} values, got {array.size}.")
    return array.reshape(expected_size)


def _unit(vector: Any) -> NDArray[np.float64]:
    vector_array = np.asarray(vector, dtype=float)
    norm = float(np.linalg.norm(vector_array))
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero-length vector.")
    return vector_array / norm


def _saturate_vector(vector: Any, max_norm: float) -> NDArray[np.float64]:
    vector_array = np.asarray(vector, dtype=float)
    norm = float(np.linalg.norm(vector_array))
    if max_norm < 0.0:
        raise ValueError("Maximum norm must be non-negative.")
    if norm == 0.0 or norm <= max_norm:
        return vector_array.copy()
    return vector_array * (max_norm / norm)


def _as_inertia_matrix(inertia_kg_m2: Any) -> NDArray[np.float64]:
    inertia = np.asarray(inertia_kg_m2, dtype=float)
    if inertia.shape == (3,):
        inertia = np.diag(inertia)
    if inertia.shape != (3, 3):
        raise ValueError("Inertia must be a 3-vector of principal moments or a 3x3 matrix.")
    return inertia


def box_inertia(
    mass_kg: float = 500.0,
    length_x_m: float = 2.0,
    length_y_m: float = 1.5,
    length_z_m: float = 1.0,
) -> NDArray[np.float64]:
    """Return the principal inertia matrix for a uniform rectangular spacecraft bus."""

    if mass_kg <= 0.0:
        raise ValueError("Mass must be positive.")
    if min(length_x_m, length_y_m, length_z_m) <= 0.0:
        raise ValueError("Box dimensions must be positive.")

    i_xx = mass_kg * (length_y_m**2 + length_z_m**2) / 12.0
    i_yy = mass_kg * (length_x_m**2 + length_z_m**2) / 12.0
    i_zz = mass_kg * (length_x_m**2 + length_y_m**2) / 12.0
    return np.diag(np.array([i_xx, i_yy, i_zz], dtype=float))


def quaternion_normalize(q: Any) -> Array4:
    """Normalize a scalar-first quaternion ``[w, x, y, z]``."""

    q_array = _as_float_array(q, 4)
    norm = float(np.linalg.norm(q_array))
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero-length quaternion.")
    return q_array / norm


def quaternion_conjugate(q: Any) -> Array4:
    q_unit = quaternion_normalize(q)
    return np.array([q_unit[0], -q_unit[1], -q_unit[2], -q_unit[3]], dtype=float)


def quaternion_multiply(left: Any, right: Any) -> Array4:
    """Multiply two scalar-first quaternions."""

    w1, x1, y1, z1 = _as_float_array(left, 4)
    w2, x2, y2, z2 = _as_float_array(right, 4)
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=float,
    )


def quaternion_rotate(q_body_to_inertial: Any, vector_body: Any) -> Array3:
    """Rotate a vector from body coordinates to inertial coordinates."""

    q_unit = quaternion_normalize(q_body_to_inertial)
    vector_quat = np.concatenate(([0.0], _as_float_array(vector_body, 3)))
    rotated = quaternion_multiply(
        quaternion_multiply(q_unit, vector_quat), quaternion_conjugate(q_unit)
    )
    return rotated[1:]


def quaternion_rotate_inverse(q_body_to_inertial: Any, vector_inertial: Any) -> Array3:
    """Rotate a vector from inertial coordinates to body coordinates."""

    return quaternion_rotate(quaternion_conjugate(q_body_to_inertial), vector_inertial)


def quaternion_derivative(q_body_to_inertial: Any, omega_body_rad_s: Any) -> Array4:
    """Return ``dq/dt`` for body rates expressed in the body frame."""

    q_unit = quaternion_normalize(q_body_to_inertial)
    omega_quat = np.concatenate(([0.0], _as_float_array(omega_body_rad_s, 3)))
    return 0.5 * quaternion_multiply(q_unit, omega_quat)


def quaternion_step(q_body_to_inertial: Any, omega_body_rad_s: Any, dt_s: float) -> Array4:
    """Propagate attitude with a constant-rate quaternion increment."""

    q_unit = quaternion_normalize(q_body_to_inertial)
    omega_body = _as_float_array(omega_body_rad_s, 3)
    angle_rad = float(np.linalg.norm(omega_body) * dt_s)
    if angle_rad == 0.0:
        return q_unit

    axis_body = omega_body / float(np.linalg.norm(omega_body))
    half_angle_rad = 0.5 * angle_rad
    delta_q = np.concatenate(
        ([np.cos(half_angle_rad)], axis_body * np.sin(half_angle_rad))
    )
    return quaternion_normalize(quaternion_multiply(q_unit, delta_q))


def gravity_gradient_torque(
    inertia_kg_m2: Any,
    r_inertial_m: Any,
    q_body_to_inertial: Any | None = None,
    mu_m3_s2: float = EARTH_MU_M3_S2,
) -> Array3:
    """Gravity-gradient torque in body axes.

    The quaternion maps body coordinates into the inertial frame. If omitted,
    body and inertial axes are assumed aligned.
    """

    inertia = _as_inertia_matrix(inertia_kg_m2)
    r_inertial = _as_float_array(r_inertial_m, 3)
    radius_m = float(np.linalg.norm(r_inertial))
    if radius_m == 0.0:
        raise ValueError("Position vector must be non-zero.")

    r_hat_inertial = r_inertial / radius_m
    if q_body_to_inertial is None:
        r_hat_body = r_hat_inertial
    else:
        r_hat_body = quaternion_rotate_inverse(q_body_to_inertial, r_hat_inertial)

    return (3.0 * mu_m3_s2 / radius_m**3) * np.cross(r_hat_body, inertia @ r_hat_body)


def magnetic_torque(magnetic_moment_a_m2: Any, magnetic_field_t: Any) -> Array3:
    """Return magnetic torque ``m x B`` in N m."""

    return np.cross(_as_float_array(magnetic_moment_a_m2, 3), _as_float_array(magnetic_field_t, 3))


def solar_radiation_pressure_torque(
    sun_hat_inertial: Any,
    q_body_to_inertial: Any,
    solar_flux_w_m2: float,
    area_m2: float,
    reflectivity_coefficient: float,
    center_of_pressure_body_m: Any,
) -> Array3:
    """Return a coarse SRP torque in body axes."""

    if solar_flux_w_m2 <= 0.0 or area_m2 <= 0.0:
        return np.zeros(3, dtype=float)
    sun_hat = _unit(sun_hat_inertial)
    force_inertial_n = (
        -float(solar_flux_w_m2)
        / SPEED_OF_LIGHT_M_S
        * float(area_m2)
        * float(reflectivity_coefficient)
        * sun_hat
    )
    force_body_n = quaternion_rotate_inverse(q_body_to_inertial, force_inertial_n)
    return np.cross(_as_float_array(center_of_pressure_body_m, 3), force_body_n)


def aerodynamic_drag_torque(
    r_inertial_m: Any,
    v_inertial_mps: Any,
    q_body_to_inertial: Any,
    density_kg_m3: float,
    drag_coefficient: float,
    area_m2: float,
    center_of_pressure_body_m: Any,
) -> Array3:
    """Return a coarse free-molecular drag torque in body axes."""

    if density_kg_m3 <= 0.0 or drag_coefficient <= 0.0 or area_m2 <= 0.0:
        return np.zeros(3, dtype=float)
    r_inertial = _as_float_array(r_inertial_m, 3)
    v_inertial = _as_float_array(v_inertial_mps, 3)
    atmosphere_velocity = np.cross(np.array([0.0, 0.0, EARTH_ROT_RATE_RAD_S]), r_inertial)
    relative_velocity = v_inertial - atmosphere_velocity
    speed_mps = float(np.linalg.norm(relative_velocity))
    if speed_mps == 0.0:
        return np.zeros(3, dtype=float)
    force_inertial_n = (
        -0.5
        * float(density_kg_m3)
        * speed_mps**2
        * float(drag_coefficient)
        * float(area_m2)
        * (relative_velocity / speed_mps)
    )
    force_body_n = quaternion_rotate_inverse(q_body_to_inertial, force_inertial_n)
    return np.cross(_as_float_array(center_of_pressure_body_m, 3), force_body_n)


def bdot_command(
    omega_body_rad_s: Any,
    magnetic_field_body_t: Any,
    gain_a_m2_per_t_s: float = 8.0e7,
    max_dipole_a_m2: float = 400.0,
) -> Array3:
    """Saturated B-dot dipole command using body-rate-induced magnetic-field change."""

    omega_body = _as_float_array(omega_body_rad_s, 3)
    magnetic_field_body = _as_float_array(magnetic_field_body_t, 3)
    b_dot_body_t_s = -np.cross(omega_body, magnetic_field_body)
    return _saturate_vector(-gain_a_m2_per_t_s * b_dot_body_t_s, max_dipole_a_m2)


def rigid_body_omega_derivative(
    inertia_kg_m2: Any,
    omega_body_rad_s: Any,
    torque_body_nm: Any,
) -> Array3:
    """Euler rigid-body angular acceleration for a fixed inertia matrix."""

    inertia = _as_inertia_matrix(inertia_kg_m2)
    omega_body = _as_float_array(omega_body_rad_s, 3)
    torque_body = _as_float_array(torque_body_nm, 3)
    angular_momentum = inertia @ omega_body
    return np.linalg.solve(inertia, torque_body - np.cross(omega_body, angular_momentum))


def rigid_body_omega_step_rk4(
    inertia_kg_m2: Any,
    omega_body_rad_s: Any,
    torque_body_nm: Any,
    dt_s: float,
) -> Array3:
    """Advance body rates with RK4 for fixed torque over one small step."""

    inertia = _as_inertia_matrix(inertia_kg_m2)
    omega = _as_float_array(omega_body_rad_s, 3)
    torque = _as_float_array(torque_body_nm, 3)
    if dt_s < 0.0:
        raise ValueError("Time step must be non-negative.")

    def derivative(candidate_omega: Array3) -> Array3:
        return rigid_body_omega_derivative(inertia, candidate_omega, torque)

    k1 = derivative(omega)
    k2 = derivative(omega + 0.5 * dt_s * k1)
    k3 = derivative(omega + 0.5 * dt_s * k2)
    k4 = derivative(omega + dt_s * k3)
    return omega + (dt_s / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def wheel_momentum_desaturation_step(
    wheel_momentum_body_nms: Any,
    absorbed_torque_body_nm: Any,
    dt_s: float,
    magnetic_field_body_t: Any | None = None,
    max_dipole_a_m2: float = 400.0,
    capacity_nms: float = 12.0,
    desat_threshold_fraction: float = 0.75,
) -> tuple[Array3, dict[str, Any]]:
    """Accumulate wheel momentum and optionally unload it with a magnetic torque.

    ``absorbed_torque_body_nm`` is the torque the wheel set must absorb over the
    step, such as a rejected disturbance. Desaturation requests a magnetic torque
    opposite the wheel momentum component that is perpendicular to the field.
    """

    if dt_s < 0.0:
        raise ValueError("Time step must be non-negative.")
    if capacity_nms <= 0.0:
        raise ValueError("Wheel momentum capacity must be positive.")

    wheel_momentum = _as_float_array(wheel_momentum_body_nms, 3)
    absorbed_torque = _as_float_array(absorbed_torque_body_nm, 3)
    updated = wheel_momentum + absorbed_torque * float(dt_s)
    desat_active = False
    desat_dipole = np.zeros(3, dtype=float)
    desat_torque = np.zeros(3, dtype=float)

    threshold_nms = desat_threshold_fraction * capacity_nms
    momentum_norm = float(np.linalg.norm(updated))
    if magnetic_field_body_t is not None and momentum_norm > threshold_nms:
        magnetic_field = _as_float_array(magnetic_field_body_t, 3)
        field_norm_sq = float(np.dot(magnetic_field, magnetic_field))
        if field_norm_sq > 0.0:
            desired_unload_torque = -updated / max(float(dt_s), 1.0)
            desired_unload_torque -= (
                np.dot(desired_unload_torque, magnetic_field) / field_norm_sq
            ) * magnetic_field
            desat_dipole = _saturate_vector(
                np.cross(magnetic_field, desired_unload_torque) / field_norm_sq,
                max_dipole_a_m2,
            )
            desat_torque = magnetic_torque(desat_dipole, magnetic_field)
            updated = updated + desat_torque * float(dt_s)
            desat_active = bool(np.linalg.norm(desat_dipole) > 0.0)

    updated_norm = float(np.linalg.norm(updated))
    saturated = updated_norm > capacity_nms
    return updated, {
        "desat_active": desat_active,
        "saturated": saturated,
        "desat_dipole_a_m2": desat_dipole,
        "desat_torque_nm": desat_torque,
        "momentum_norm_nms": updated_norm,
        "capacity_margin_nms": capacity_nms - updated_norm,
    }


def _mission_and_adcs_config(
    config: MissionConfig | AdcsConfig | None,
) -> tuple[MissionConfig, AdcsConfig]:
    if config is None:
        return default_mission_config(), AdcsConfig()
    if isinstance(config, AdcsConfig):
        return default_mission_config(), config
    return config, getattr(config, "adcs", AdcsConfig())


def _initial_omega(initial_tumble_rad_s: float) -> Array3:
    direction = np.array([1.0, 0.0, 0.0], dtype=float)
    return direction * initial_tumble_rad_s


def _row_vector(row: pd.Series, names: tuple[str, str, str]) -> Array3:
    return np.array([float(row[names[0]]), float(row[names[1]]), float(row[names[2]])], dtype=float)


def _row_vector_or_zero(row: pd.Series, names: tuple[str, str, str]) -> Array3:
    if set(names).issubset(row.index):
        return _row_vector(row, names)
    return np.zeros(3, dtype=float)


def _magnetic_field_from_row(row: pd.Series, r_inertial_m: Array3) -> Array3:
    if {"b_eci_x_t", "b_eci_y_t", "b_eci_z_t"}.issubset(row.index):
        return _row_vector(row, ("b_eci_x_t", "b_eci_y_t", "b_eci_z_t"))

    r_hat = _unit(r_inertial_m)
    dipole_hat = np.array([0.0, 0.0, 1.0], dtype=float)
    scale = EARTH_EQUATORIAL_B_T * (EARTH_RADIUS_M / np.linalg.norm(r_inertial_m)) ** 3
    return scale * (3.0 * np.dot(dipole_hat, r_hat) * r_hat - dipole_hat)


def _substep_count(dt_s: float, max_internal_step_s: float) -> int:
    if dt_s <= 0.0:
        return 1
    return max(1, int(np.ceil(dt_s / max_internal_step_s)))


def _output_times(duration_s: float, step_s: float) -> NDArray[np.float64]:
    count = int(np.floor(duration_s / step_s)) + 1
    times_s = np.arange(count, dtype=float) * step_s
    if times_s[-1] < duration_s:
        times_s = np.append(times_s, duration_s)
    return times_s


def _record_state(
    t_s: float,
    q_body_to_inertial: Array4,
    omega_body_rad_s: Array3,
    gravity_torque_body_nm: Array3,
    magnetic_torque_body_nm: Array3,
    srp_torque_body_nm: Array3,
    drag_torque_body_nm: Array3,
    residual_magnetic_torque_body_nm: Array3,
    total_torque_body_nm: Array3,
    magnetic_field_body_t: Array3,
    magnetic_dipole_body_a_m2: Array3,
    wheel_momentum_body_nms: Array3,
    wheel_info: dict[str, Any],
    inertia_kg_m2: Array3,
) -> dict[str, float | bool]:
    angular_momentum_body_nms = inertia_kg_m2 @ omega_body_rad_s
    q_norm = float(np.linalg.norm(q_body_to_inertial))
    return {
        "t_s": float(t_s),
        "q_w": float(q_body_to_inertial[0]),
        "q_x": float(q_body_to_inertial[1]),
        "q_y": float(q_body_to_inertial[2]),
        "q_z": float(q_body_to_inertial[3]),
        "omega_x_rad_s": float(omega_body_rad_s[0]),
        "omega_y_rad_s": float(omega_body_rad_s[1]),
        "omega_z_rad_s": float(omega_body_rad_s[2]),
        "angular_speed_rad_s": float(np.linalg.norm(omega_body_rad_s)),
        "angular_speed_deg_s": float(np.linalg.norm(omega_body_rad_s) * RAD2DEG),
        "q_norm": q_norm,
        "rotational_kinetic_energy_j": float(
            0.5 * omega_body_rad_s @ inertia_kg_m2 @ omega_body_rad_s
        ),
        "angular_momentum_norm_nms": float(np.linalg.norm(angular_momentum_body_nms)),
        "magnetic_field_norm_t": float(np.linalg.norm(magnetic_field_body_t)),
        "gravity_gradient_torque_x_nm": float(gravity_torque_body_nm[0]),
        "gravity_gradient_torque_y_nm": float(gravity_torque_body_nm[1]),
        "gravity_gradient_torque_z_nm": float(gravity_torque_body_nm[2]),
        "srp_torque_x_nm": float(srp_torque_body_nm[0]),
        "srp_torque_y_nm": float(srp_torque_body_nm[1]),
        "srp_torque_z_nm": float(srp_torque_body_nm[2]),
        "drag_torque_x_nm": float(drag_torque_body_nm[0]),
        "drag_torque_y_nm": float(drag_torque_body_nm[1]),
        "drag_torque_z_nm": float(drag_torque_body_nm[2]),
        "residual_magnetic_torque_x_nm": float(residual_magnetic_torque_body_nm[0]),
        "residual_magnetic_torque_y_nm": float(residual_magnetic_torque_body_nm[1]),
        "residual_magnetic_torque_z_nm": float(residual_magnetic_torque_body_nm[2]),
        "magnetic_torque_x_nm": float(magnetic_torque_body_nm[0]),
        "magnetic_torque_y_nm": float(magnetic_torque_body_nm[1]),
        "magnetic_torque_z_nm": float(magnetic_torque_body_nm[2]),
        "total_torque_x_nm": float(total_torque_body_nm[0]),
        "total_torque_y_nm": float(total_torque_body_nm[1]),
        "total_torque_z_nm": float(total_torque_body_nm[2]),
        "commanded_dipole_x_a_m2": float(magnetic_dipole_body_a_m2[0]),
        "commanded_dipole_y_a_m2": float(magnetic_dipole_body_a_m2[1]),
        "commanded_dipole_z_a_m2": float(magnetic_dipole_body_a_m2[2]),
        "wheel_momentum_x_nms": float(wheel_momentum_body_nms[0]),
        "wheel_momentum_y_nms": float(wheel_momentum_body_nms[1]),
        "wheel_momentum_z_nms": float(wheel_momentum_body_nms[2]),
        "wheel_momentum_norm_nms": float(np.linalg.norm(wheel_momentum_body_nms)),
        "wheel_desat_active_flag": bool(wheel_info.get("desat_active", False)),
        "wheel_saturated_flag": bool(wheel_info.get("saturated", False)),
    }


def _attitude_control_terms(
    inertia_kg_m2: NDArray[np.float64],
    q_body_to_inertial: Array4,
    omega_body_rad_s: Array3,
    r_inertial_m: Array3,
    v_inertial_mps: Array3,
    sun_hat_inertial: Array3,
    solar_flux_w_m2: float,
    atmospheric_density_kg_m3: float,
    magnetic_field_inertial_t: Array3,
    adcs_config: AdcsConfig,
) -> tuple[Array3, Array3, Array3, Array3, Array3, Array3, Array3]:
    magnetic_field_body_t = quaternion_rotate_inverse(q_body_to_inertial, magnetic_field_inertial_t)
    gravity_torque_body_nm = gravity_gradient_torque(
        inertia_kg_m2, r_inertial_m, q_body_to_inertial
    )
    srp_torque_body_nm = solar_radiation_pressure_torque(
        sun_hat_inertial,
        q_body_to_inertial,
        solar_flux_w_m2,
        adcs_config.srp_area_m2,
        adcs_config.srp_reflectivity_coefficient,
        adcs_config.srp_center_of_pressure_body_m,
    )
    drag_torque_body_nm = aerodynamic_drag_torque(
        r_inertial_m,
        v_inertial_mps,
        q_body_to_inertial,
        atmospheric_density_kg_m3,
        adcs_config.drag_coefficient,
        adcs_config.drag_area_m2,
        adcs_config.drag_center_of_pressure_body_m,
    )
    residual_magnetic_torque_body_nm = magnetic_torque(
        adcs_config.residual_dipole_body_a_m2, magnetic_field_body_t
    )
    field_norm_sq = float(np.dot(magnetic_field_body_t, magnetic_field_body_t))
    if field_norm_sq > 0.0:
        field_hat = magnetic_field_body_t / np.sqrt(field_norm_sq)
        omega_perpendicular = omega_body_rad_s - np.dot(omega_body_rad_s, field_hat) * field_hat
        desired_torque_body_nm = -adcs_config.magnetic_damping_nms * omega_perpendicular
        max_torque_nm = adcs_config.magnetorquer_max_dipole_a_m2 * np.sqrt(field_norm_sq)
        desired_torque_body_nm = _saturate_vector(desired_torque_body_nm, max_torque_nm)
        dipole_body_a_m2 = _saturate_vector(
            np.cross(magnetic_field_body_t, desired_torque_body_nm) / field_norm_sq,
            adcs_config.magnetorquer_max_dipole_a_m2,
        )
    else:
        dipole_body_a_m2 = np.zeros(3, dtype=float)
    magnetic_torque_body_nm = magnetic_torque(dipole_body_a_m2, magnetic_field_body_t)
    return (
        gravity_torque_body_nm,
        magnetic_torque_body_nm,
        srp_torque_body_nm,
        drag_torque_body_nm,
        residual_magnetic_torque_body_nm,
        dipole_body_a_m2,
        magnetic_field_body_t,
    )


def bdot_detumble_demo(
    duration_s: float = 3600.0,
    step_s: float = 1.0,
    inertia_kg_m2: Any | None = None,
    initial_omega_rad_s: Any | None = None,
    magnetic_field_inertial_t: Any | None = None,
    max_dipole_a_m2: float = 400.0,
    gain_a_m2_per_t_s: float = 8.0e7,
    max_internal_step_s: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run a deterministic fixed-field B-dot detumble demonstration."""

    if duration_s < 0.0:
        raise ValueError("Duration must be non-negative.")
    if step_s <= 0.0:
        raise ValueError("Step size must be positive.")
    if max_internal_step_s <= 0.0:
        raise ValueError("Internal step size must be positive.")

    inertia = (
        box_inertia()
        if inertia_kg_m2 is None
        else _as_inertia_matrix(inertia_kg_m2)
    )
    omega_body_rad_s = (
        _initial_omega(10.0 * DEG2RAD)
        if initial_omega_rad_s is None
        else _as_float_array(initial_omega_rad_s, 3)
    )
    magnetic_field_inertial = (
        np.array([2.0e-5, -1.0e-5, 2.5e-5], dtype=float)
        if magnetic_field_inertial_t is None
        else _as_float_array(magnetic_field_inertial_t, 3)
    )
    q_body_to_inertial = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)

    times = _output_times(duration_s, step_s)
    records: list[dict[str, float]] = []

    for time_index, t_s in enumerate(times):
        magnetic_field_body = quaternion_rotate_inverse(
            q_body_to_inertial, magnetic_field_inertial
        )
        dipole_body = bdot_command(
            omega_body_rad_s,
            magnetic_field_body,
            gain_a_m2_per_t_s=gain_a_m2_per_t_s,
            max_dipole_a_m2=max_dipole_a_m2,
        )
        torque_body = magnetic_torque(dipole_body, magnetic_field_body)
        records.append(
            {
                "t_s": float(t_s),
                "angular_speed_rad_s": float(np.linalg.norm(omega_body_rad_s)),
                "angular_speed_deg_s": float(np.linalg.norm(omega_body_rad_s) * RAD2DEG),
                "dipole_norm_a_m2": float(np.linalg.norm(dipole_body)),
                "magnetic_torque_norm_nm": float(np.linalg.norm(torque_body)),
            }
        )
        if time_index == len(times) - 1:
            continue

        dt_total_s = float(times[time_index + 1] - t_s)
        substeps = _substep_count(dt_total_s, max_internal_step_s)
        dt_s = dt_total_s / substeps
        for _ in range(substeps):
            magnetic_field_body = quaternion_rotate_inverse(
                q_body_to_inertial, magnetic_field_inertial
            )
            dipole_body = bdot_command(
                omega_body_rad_s,
                magnetic_field_body,
                gain_a_m2_per_t_s=gain_a_m2_per_t_s,
                max_dipole_a_m2=max_dipole_a_m2,
            )
            torque_body = magnetic_torque(dipole_body, magnetic_field_body)
            omega_body_rad_s = rigid_body_omega_step_rk4(
                inertia, omega_body_rad_s, torque_body, dt_s
            )
            q_body_to_inertial = quaternion_step(q_body_to_inertial, omega_body_rad_s, dt_s)

    history = pd.DataFrame(records)
    summary = {
        "initial_angular_speed_deg_s": float(history["angular_speed_deg_s"].iloc[0]),
        "final_angular_speed_deg_s": float(history["angular_speed_deg_s"].iloc[-1]),
        "max_dipole_a_m2": float(max_dipole_a_m2),
        "duration_s": float(duration_s),
    }
    return history, summary


@dataclass(frozen=True)
class SunPointingConfig:
    """Reaction-wheel PD sun-pointing controller gains and target."""

    proportional_gain_nm: float = 0.8
    derivative_gain_nms: float = 30.0
    target_body_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    settle_error_deg: float = 3.0
    internal_step_s: float = 3.0


def run_sun_pointing(
    environment_df: pd.DataFrame,
    config: MissionConfig | AdcsConfig | None = None,
    pointing: SunPointingConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float | bool]]:
    """Closed-loop PD sun-pointing on reaction wheels, reporting pointing error.

    Starts from a detumbled state and slews a chosen body axis onto the Sun line,
    then holds it against gravity-gradient/SRP disturbances. This provides the
    brief's "attitude angle error (deg) sun-pointing accuracy" output.
    """

    if environment_df.empty:
        raise ValueError("Environment table must contain at least one row.")
    mission_config, adcs_config = _mission_and_adcs_config(config)
    pointing_config = pointing or SunPointingConfig()
    spacecraft = mission_config.spacecraft
    inertia = box_inertia(
        spacecraft.mass_kg, spacecraft.length_x_m, spacecraft.length_y_m, spacecraft.length_z_m
    )
    target_axis_body = _unit(pointing_config.target_body_axis)

    environment = environment_df.sort_values("t_s").reset_index(drop=True)
    q_body_to_inertial = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    omega_body_rad_s = np.zeros(3, dtype=float)
    wheel_momentum_body_nms = np.zeros(3, dtype=float)
    records: list[dict[str, float]] = []

    def pointing_error_deg(q: Array4, sun_hat_inertial: Array3) -> tuple[float, Array3]:
        sun_body = quaternion_rotate_inverse(q, sun_hat_inertial)
        cos_angle = float(np.clip(np.dot(target_axis_body, sun_body), -1.0, 1.0))
        error_axis_body = np.cross(target_axis_body, sun_body)
        return float(np.degrees(np.arccos(cos_angle))), error_axis_body

    for row_index, row in environment.iterrows():
        r_inertial_m = _row_vector(row, ("x_eci_m", "y_eci_m", "z_eci_m"))
        sun_hat_inertial = _row_vector_or_zero(row, ("sun_hat_x", "sun_hat_y", "sun_hat_z"))
        if np.linalg.norm(sun_hat_inertial) == 0.0:
            sun_hat_inertial = np.array([1.0, 0.0, 0.0], dtype=float)
        sun_hat_inertial = _unit(sun_hat_inertial)

        error_deg, _ = pointing_error_deg(q_body_to_inertial, sun_hat_inertial)
        records.append(
            {
                "t_s": float(row["t_s"]),
                "q_w": float(q_body_to_inertial[0]),
                "q_x": float(q_body_to_inertial[1]),
                "q_y": float(q_body_to_inertial[2]),
                "q_z": float(q_body_to_inertial[3]),
                "pointing_error_deg": error_deg,
                "angular_speed_deg_s": float(np.linalg.norm(omega_body_rad_s) * RAD2DEG),
                "wheel_momentum_norm_nms": float(np.linalg.norm(wheel_momentum_body_nms)),
                "q_norm": float(np.linalg.norm(q_body_to_inertial)),
            }
        )
        if row_index == len(environment) - 1:
            continue

        dt_total_s = float(environment.loc[row_index + 1, "t_s"]) - float(row["t_s"])
        substeps = _substep_count(dt_total_s, pointing_config.internal_step_s)
        dt_s = dt_total_s / substeps
        for _ in range(substeps):
            _, error_axis_body = pointing_error_deg(q_body_to_inertial, sun_hat_inertial)
            control_torque_body = (
                pointing_config.proportional_gain_nm * error_axis_body
                - pointing_config.derivative_gain_nms * omega_body_rad_s
            )
            disturbance_body = gravity_gradient_torque(
                inertia, r_inertial_m, q_body_to_inertial
            )
            total_torque_body = control_torque_body + disturbance_body
            omega_body_rad_s = rigid_body_omega_step_rk4(
                inertia, omega_body_rad_s, total_torque_body, dt_s
            )
            q_body_to_inertial = quaternion_step(q_body_to_inertial, omega_body_rad_s, dt_s)
            wheel_momentum_body_nms = wheel_momentum_body_nms - control_torque_body * dt_s

    timeseries = pd.DataFrame(records)
    settled = timeseries[timeseries["t_s"] >= timeseries["t_s"].iloc[-1] * 0.5]
    summary: dict[str, float | bool] = {
        "initial_pointing_error_deg": float(timeseries["pointing_error_deg"].iloc[0]),
        "final_pointing_error_deg": float(timeseries["pointing_error_deg"].iloc[-1]),
        "settled_mean_pointing_error_deg": float(settled["pointing_error_deg"].mean()),
        "settled_max_pointing_error_deg": float(settled["pointing_error_deg"].max()),
        "pointing_requirement_met": bool(
            settled["pointing_error_deg"].max() <= pointing_config.settle_error_deg
        ),
        "max_wheel_momentum_nms": float(timeseries["wheel_momentum_norm_nms"].max()),
        "max_q_norm_error": float(np.max(np.abs(timeseries["q_norm"].to_numpy() - 1.0))),
        "settle_error_deg": float(pointing_config.settle_error_deg),
    }
    return timeseries, summary


def run_adcs(
    environment_df: pd.DataFrame,
    config: MissionConfig | AdcsConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float | bool]]:
    """Run a deterministic first-order ADCS simulation over an environment table."""

    if environment_df.empty:
        raise ValueError("Environment table must contain at least one row.")
    required_columns = {"t_s", "x_eci_m", "y_eci_m", "z_eci_m"}
    missing = required_columns.difference(environment_df.columns)
    if missing:
        raise ValueError(f"Environment table is missing columns: {sorted(missing)}")

    mission_config, adcs_config = _mission_and_adcs_config(config)
    spacecraft = mission_config.spacecraft
    inertia = box_inertia(
        spacecraft.mass_kg,
        spacecraft.length_x_m,
        spacecraft.length_y_m,
        spacecraft.length_z_m,
    )

    environment = environment_df.sort_values("t_s").reset_index(drop=True)
    q_body_to_inertial = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    omega_body_rad_s = _initial_omega(adcs_config.initial_tumble_rad_s)
    wheel_momentum_body_nms = np.zeros(3, dtype=float)
    wheel_info: dict[str, Any] = {
        "desat_active": False,
        "saturated": False,
        "momentum_norm_nms": 0.0,
    }
    records: list[dict[str, float | bool]] = []
    desat_count = 0

    for row_index, row in environment.iterrows():
        r_inertial_m = _row_vector(row, ("x_eci_m", "y_eci_m", "z_eci_m"))
        v_inertial_mps = _row_vector_or_zero(row, ("vx_eci_mps", "vy_eci_mps", "vz_eci_mps"))
        sun_hat_inertial = _row_vector_or_zero(row, ("sun_hat_x", "sun_hat_y", "sun_hat_z"))
        if np.linalg.norm(sun_hat_inertial) == 0.0:
            sun_hat_inertial = np.array([1.0, 0.0, 0.0], dtype=float)
        solar_flux_w_m2 = float(row.get("solar_flux_w_m2", 0.0))
        atmospheric_density_kg_m3 = float(row.get("atmospheric_density_kg_m3", 0.0))
        magnetic_field_inertial_t = _magnetic_field_from_row(row, r_inertial_m)
        (
            gravity_torque_body_nm,
            magnetic_torque_body_nm,
            srp_torque_body_nm,
            drag_torque_body_nm,
            residual_magnetic_torque_body_nm,
            dipole_body_a_m2,
            magnetic_field_body_t,
        ) = _attitude_control_terms(
            inertia,
            q_body_to_inertial,
            omega_body_rad_s,
            r_inertial_m,
            v_inertial_mps,
            sun_hat_inertial,
            solar_flux_w_m2,
            atmospheric_density_kg_m3,
            magnetic_field_inertial_t,
            adcs_config,
        )
        environmental_torque_body_nm = (
            gravity_torque_body_nm
            + srp_torque_body_nm
            + drag_torque_body_nm
            + residual_magnetic_torque_body_nm
        )
        total_torque_body_nm = environmental_torque_body_nm + magnetic_torque_body_nm

        records.append(
            _record_state(
                float(row["t_s"]),
                q_body_to_inertial,
                omega_body_rad_s,
                gravity_torque_body_nm,
                magnetic_torque_body_nm,
                srp_torque_body_nm,
                drag_torque_body_nm,
                residual_magnetic_torque_body_nm,
                total_torque_body_nm,
                magnetic_field_body_t,
                dipole_body_a_m2,
                wheel_momentum_body_nms,
                wheel_info,
                inertia,
            )
        )
        if row_index == len(environment) - 1:
            continue

        next_t_s = float(environment.loc[row_index + 1, "t_s"])
        dt_total_s = next_t_s - float(row["t_s"])
        if dt_total_s < 0.0:
            raise ValueError("Environment times must be monotonically increasing.")
        substeps = _substep_count(dt_total_s, adcs_config.max_internal_step_s)
        dt_s = dt_total_s / substeps if substeps > 0 else 0.0

        for _ in range(substeps):
            (
                gravity_torque_body_nm,
                magnetic_torque_body_nm,
                srp_torque_body_nm,
                drag_torque_body_nm,
                residual_magnetic_torque_body_nm,
                dipole_body_a_m2,
                magnetic_field_body_t,
            ) = _attitude_control_terms(
                inertia,
                q_body_to_inertial,
                omega_body_rad_s,
                r_inertial_m,
                v_inertial_mps,
                sun_hat_inertial,
                solar_flux_w_m2,
                atmospheric_density_kg_m3,
                magnetic_field_inertial_t,
                adcs_config,
            )
            environmental_torque_body_nm = (
                gravity_torque_body_nm
                + srp_torque_body_nm
                + drag_torque_body_nm
                + residual_magnetic_torque_body_nm
            )
            total_torque_body_nm = environmental_torque_body_nm + magnetic_torque_body_nm
            omega_body_rad_s = rigid_body_omega_step_rk4(
                inertia, omega_body_rad_s, total_torque_body_nm, dt_s
            )
            q_body_to_inertial = quaternion_step(q_body_to_inertial, omega_body_rad_s, dt_s)

            wheel_momentum_body_nms, wheel_info = wheel_momentum_desaturation_step(
                wheel_momentum_body_nms,
                environmental_torque_body_nm,
                dt_s,
                magnetic_field_body_t=magnetic_field_body_t,
                max_dipole_a_m2=0.25 * adcs_config.magnetorquer_max_dipole_a_m2,
                capacity_nms=adcs_config.wheel_momentum_capacity_nms,
                desat_threshold_fraction=adcs_config.wheel_desat_threshold_fraction,
            )
            desat_count += int(bool(wheel_info["desat_active"]))

    timeseries = pd.DataFrame(records)
    summary: dict[str, float | bool] = {
        "initial_angular_speed_deg_s": float(timeseries["angular_speed_deg_s"].iloc[0]),
        "final_angular_speed_deg_s": float(timeseries["angular_speed_deg_s"].iloc[-1]),
        "max_commanded_dipole_a_m2": float(
            np.linalg.norm(
                timeseries[
                    [
                        "commanded_dipole_x_a_m2",
                        "commanded_dipole_y_a_m2",
                        "commanded_dipole_z_a_m2",
                    ]
                ].to_numpy(dtype=float),
                axis=1,
            ).max()
        ),
        "max_wheel_momentum_nms": float(timeseries["wheel_momentum_norm_nms"].max()),
        "wheel_saturated": bool(timeseries["wheel_saturated_flag"].any()),
        "desaturation_events": float(desat_count),
        "wheel_momentum_capacity_nms": float(adcs_config.wheel_momentum_capacity_nms),
        "magnetorquer_max_dipole_a_m2": float(adcs_config.magnetorquer_max_dipole_a_m2),
        "max_total_torque_nm": float(
            np.linalg.norm(
                timeseries[["total_torque_x_nm", "total_torque_y_nm", "total_torque_z_nm"]]
                .to_numpy(dtype=float),
                axis=1,
            ).max()
        ),
        "max_disturbance_torque_nm": float(
            np.linalg.norm(
                (
                    timeseries[
                        [
                            "gravity_gradient_torque_x_nm",
                            "gravity_gradient_torque_y_nm",
                            "gravity_gradient_torque_z_nm",
                        ]
                    ].to_numpy(dtype=float)
                    + timeseries[["srp_torque_x_nm", "srp_torque_y_nm", "srp_torque_z_nm"]]
                    .to_numpy(dtype=float)
                    + timeseries[["drag_torque_x_nm", "drag_torque_y_nm", "drag_torque_z_nm"]]
                    .to_numpy(dtype=float)
                    + timeseries[
                        [
                            "residual_magnetic_torque_x_nm",
                            "residual_magnetic_torque_y_nm",
                            "residual_magnetic_torque_z_nm",
                        ]
                    ].to_numpy(dtype=float)
                ),
                axis=1,
            ).max()
        ),
        "max_q_norm_error": float(np.max(np.abs(timeseries["q_norm"].to_numpy(dtype=float) - 1.0))),
        "control_mode_scope": "B-dot detumble and disturbance torque bookkeeping",
        "pointing_validation_scope": "not included in the baseline model",
        "wheel_model_scope": "preliminary disturbance momentum bookkeeping, not closed-loop sizing",
    }
    return timeseries, summary
