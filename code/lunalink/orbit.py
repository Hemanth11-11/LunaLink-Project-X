"""Orbit propagation utilities for the LunaLink simulator."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from .config import MissionConfig, OrbitConfig
from .constants import EARTH_J2, EARTH_J3, EARTH_MU_M3_S2, EARTH_RADIUS_M
from .frames import rot_x, rot_z


@dataclass(frozen=True)
class CartesianState:
    r_eci_m: NDArray[np.float64]
    v_eci_mps: NDArray[np.float64]


def orbital_elements_to_state(orbit: OrbitConfig) -> CartesianState:
    """Convert the configured Keplerian elements to an ECI state."""

    a_m = orbit.semi_major_axis_m
    e = orbit.eccentricity
    nu = orbit.true_anomaly_at_epoch_rad
    p_m = a_m * (1.0 - e**2)

    r_pqw_m = (p_m / (1.0 + e * np.cos(nu))) * np.array(
        [np.cos(nu), np.sin(nu), 0.0], dtype=float
    )
    v_pqw_mps = np.sqrt(EARTH_MU_M3_S2 / p_m) * np.array(
        [-np.sin(nu), e + np.cos(nu), 0.0], dtype=float
    )

    transform_pqw_to_eci = (
        rot_z(orbit.raan_rad) @ rot_x(orbit.inclination_rad) @ rot_z(orbit.argument_of_perigee_rad)
    )
    return CartesianState(
        r_eci_m=transform_pqw_to_eci @ r_pqw_m,
        v_eci_mps=transform_pqw_to_eci @ v_pqw_mps,
    )


def two_body_acceleration(r_eci_m: NDArray[np.float64]) -> NDArray[np.float64]:
    radius_m = np.linalg.norm(r_eci_m)
    return -EARTH_MU_M3_S2 * r_eci_m / radius_m**3


def j2_acceleration(r_eci_m: NDArray[np.float64]) -> NDArray[np.float64]:
    x_m, y_m, z_m = r_eci_m
    radius_m = np.linalg.norm(r_eci_m)
    z_ratio_sq = (z_m / radius_m) ** 2
    scale = 1.5 * EARTH_J2 * EARTH_MU_M3_S2 * EARTH_RADIUS_M**2 / radius_m**5

    return scale * np.array(
        [
            x_m * (5.0 * z_ratio_sq - 1.0),
            y_m * (5.0 * z_ratio_sq - 1.0),
            z_m * (5.0 * z_ratio_sq - 3.0),
        ],
        dtype=float,
    )


def j3_acceleration(r_eci_m: NDArray[np.float64]) -> NDArray[np.float64]:
    """J3 zonal-harmonic acceleration (gradient of the J3 geopotential term)."""

    x_m, y_m, z_m = r_eci_m
    radius_m = np.linalg.norm(r_eci_m)
    coefficient = EARTH_MU_M3_S2 * EARTH_J3 * EARTH_RADIUS_M**3 / 2.0
    radius_pow7 = radius_m**7
    lateral = 5.0 * coefficient / radius_pow7 * z_m * (7.0 * z_m**2 / radius_m**2 - 3.0)
    return np.array(
        [
            lateral * x_m,
            lateral * y_m,
            coefficient
            / radius_pow7
            * (3.0 * radius_m**2 - 30.0 * z_m**2 + 35.0 * z_m**4 / radius_m**2),
        ],
        dtype=float,
    )


def third_body_acceleration(
    r_sc_eci_m: NDArray[np.float64], r_body_eci_m: NDArray[np.float64], mu_body_m3_s2: float
) -> NDArray[np.float64]:
    """Perturbing acceleration from a third body at ``r_body`` on the spacecraft."""

    relative_m = r_body_eci_m - r_sc_eci_m
    return mu_body_m3_s2 * (
        relative_m / np.linalg.norm(relative_m) ** 3
        - r_body_eci_m / np.linalg.norm(r_body_eci_m) ** 3
    )


def acceleration(r_eci_m: NDArray[np.float64], include_j2: bool = True) -> NDArray[np.float64]:
    total = two_body_acceleration(r_eci_m)
    if include_j2:
        total = total + j2_acceleration(r_eci_m)
    return total


def _state_derivative(
    _t_s: float, state: NDArray[np.float64], include_j2: bool
) -> NDArray[np.float64]:
    r_eci_m = state[:3]
    v_eci_mps = state[3:]
    return np.concatenate((v_eci_mps, acceleration(r_eci_m, include_j2=include_j2)))


def output_times(duration_s: float, step_s: float) -> NDArray[np.float64]:
    count = int(np.floor(duration_s / step_s)) + 1
    times_s = np.arange(count, dtype=float) * step_s
    if times_s[-1] < duration_s:
        times_s = np.append(times_s, duration_s)
    return times_s


def propagate_orbit(config: MissionConfig, include_j2: bool = True) -> pd.DataFrame:
    """Propagate the LunaLink orbit and return ECI state history."""

    initial = orbital_elements_to_state(config.orbit)
    y0 = np.concatenate((initial.r_eci_m, initial.v_eci_mps))
    times_s = output_times(config.simulation.duration_s, config.simulation.output_step_s)

    solution = solve_ivp(
        _state_derivative,
        t_span=(0.0, config.simulation.duration_s),
        y0=y0,
        args=(include_j2,),
        t_eval=times_s,
        rtol=1e-9,
        atol=1e-3,
    )
    if not solution.success:
        raise RuntimeError(f"Orbit propagation failed: {solution.message}")

    states = solution.y.T
    radius_m = np.linalg.norm(states[:, :3], axis=1)
    speed_mps = np.linalg.norm(states[:, 3:], axis=1)
    altitude_m = radius_m - EARTH_RADIUS_M

    return pd.DataFrame(
        {
            "t_s": solution.t,
            "x_eci_m": states[:, 0],
            "y_eci_m": states[:, 1],
            "z_eci_m": states[:, 2],
            "vx_eci_mps": states[:, 3],
            "vy_eci_mps": states[:, 4],
            "vz_eci_mps": states[:, 5],
            "radius_m": radius_m,
            "speed_mps": speed_mps,
            "altitude_m": altitude_m,
        }
    )


def specific_energy(r_eci_m: NDArray[np.float64], v_eci_mps: NDArray[np.float64]) -> float:
    return 0.5 * float(np.dot(v_eci_mps, v_eci_mps)) - EARTH_MU_M3_S2 / float(
        np.linalg.norm(r_eci_m)
    )
