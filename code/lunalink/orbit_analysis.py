"""High-fidelity orbit analysis for LunaLink.

Adds luni-solar third-body + J3 perturbations on top of the transparent
two-body + J2 propagator, and the classical secular-rate theory that explains
why the brief's 63.4 deg (critical) inclination freezes the argument of perigee.

Validated against Orekit 13.1 (8x8 gravity + luni-solar); see
``outputs/baseline/external_validation/spice_orekit_crosscheck.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from .config import MissionConfig, OrbitConfig
from .constants import (
    ASTRONOMICAL_UNIT_M,
    EARTH_J2,
    EARTH_MU_M3_S2,
    EARTH_RADIUS_M,
    MOON_MU_M3_S2,
    SUN_MU_M3_S2,
)
from .environment import (
    approximate_moon_position_eci_m,
    approximate_sun_hat_eci,
    parse_epoch_utc,
)
from .orbit import (
    j2_acceleration,
    j3_acceleration,
    orbital_elements_to_state,
    third_body_acceleration,
    two_body_acceleration,
)

CRITICAL_INCLINATION_RAD = math.acos(math.sqrt(1.0 / 5.0))


def secular_rates_rad_s(a_m: float, e: float, inclination_rad: float) -> tuple[float, float]:
    """First-order J2 secular rates of RAAN and argument of perigee (rad/s).

    Vallado, *Fundamentals of Astrodynamics and Applications*, Eqs. 9-38/9-39.
    """

    mean_motion = math.sqrt(EARTH_MU_M3_S2 / a_m**3)
    semi_latus_rectum = a_m * (1.0 - e**2)
    factor = mean_motion * EARTH_J2 * (EARTH_RADIUS_M / semi_latus_rectum) ** 2
    raan_rate = -1.5 * factor * math.cos(inclination_rad)
    argp_rate = 0.75 * factor * (5.0 * math.cos(inclination_rad) ** 2 - 1.0)
    return raan_rate, argp_rate


def frozen_apsides_scan(
    orbit: OrbitConfig, inclinations_deg: NDArray | None = None
) -> pd.DataFrame:
    """Analytic argument-of-perigee drift versus inclination.

    The drift crosses zero at the critical inclination (~63.43 deg), which is why
    the LunaLink Molniya orbit holds its apogee over the northern hemisphere.
    """

    if inclinations_deg is None:
        inclinations_deg = np.linspace(0.0, 90.0, 181)
    a_m = orbit.semi_major_axis_m
    e = orbit.eccentricity
    rows = []
    for inclination_deg in np.asarray(inclinations_deg, dtype=float):
        raan_rate, argp_rate = secular_rates_rad_s(a_m, e, math.radians(inclination_deg))
        rows.append(
            {
                "inclination_deg": float(inclination_deg),
                "argp_rate_deg_per_day": math.degrees(argp_rate) * 86400.0,
                "raan_rate_deg_per_day": math.degrees(raan_rate) * 86400.0,
            }
        )
    return pd.DataFrame(rows)


def rv_to_classical_elements(
    r_eci_m: NDArray[np.float64], v_eci_mps: NDArray[np.float64]
) -> dict[str, float]:
    """Osculating classical elements from an ECI state (angles in radians)."""

    r_vec = np.asarray(r_eci_m, dtype=float)
    v_vec = np.asarray(v_eci_mps, dtype=float)
    radius = float(np.linalg.norm(r_vec))
    speed = float(np.linalg.norm(v_vec))
    h_vec = np.cross(r_vec, v_vec)
    h_mag = float(np.linalg.norm(h_vec))
    node_vec = np.cross([0.0, 0.0, 1.0], h_vec)
    node_mag = float(np.linalg.norm(node_vec))

    e_vec = (
        (speed**2 - EARTH_MU_M3_S2 / radius) * r_vec - float(np.dot(r_vec, v_vec)) * v_vec
    ) / EARTH_MU_M3_S2
    eccentricity = float(np.linalg.norm(e_vec))
    energy = speed**2 / 2.0 - EARTH_MU_M3_S2 / radius
    semi_major_axis = -EARTH_MU_M3_S2 / (2.0 * energy)
    inclination = math.acos(max(-1.0, min(1.0, h_vec[2] / h_mag)))

    raan = math.atan2(node_vec[1], node_vec[0]) % (2.0 * math.pi) if node_mag > 0 else 0.0
    if node_mag > 0 and eccentricity > 1e-9:
        argp = math.acos(
            max(-1.0, min(1.0, float(np.dot(node_vec, e_vec)) / (node_mag * eccentricity)))
        )
        if e_vec[2] < 0:
            argp = 2.0 * math.pi - argp
    else:
        argp = 0.0
    return {
        "a_m": semi_major_axis,
        "e": eccentricity,
        "i_rad": inclination,
        "raan_rad": raan,
        "argp_rad": argp,
    }


def _high_fidelity_rhs(t_s, state, epoch, include_j3, include_third_body):
    r_eci_m = state[:3]
    velocity = state[3:]
    accel = two_body_acceleration(r_eci_m) + j2_acceleration(r_eci_m)
    if include_j3:
        accel = accel + j3_acceleration(r_eci_m)
    if include_third_body:
        sun_pos_m = approximate_sun_hat_eci(epoch, t_s) * ASTRONOMICAL_UNIT_M
        moon_pos_m = approximate_moon_position_eci_m(epoch, t_s)
        accel = accel + third_body_acceleration(r_eci_m, sun_pos_m, SUN_MU_M3_S2)
        accel = accel + third_body_acceleration(r_eci_m, moon_pos_m, MOON_MU_M3_S2)
    return np.concatenate((velocity, accel))


def propagate_high_fidelity(
    config: MissionConfig,
    *,
    duration_s: float,
    output_step_s: float,
    include_j3: bool = True,
    include_third_body: bool = True,
) -> pd.DataFrame:
    """Propagate with two-body + J2 + J3 + luni-solar third-body perturbations."""

    epoch = parse_epoch_utc(config.simulation.epoch_utc)
    initial = orbital_elements_to_state(config.orbit)
    y0 = np.concatenate((initial.r_eci_m, initial.v_eci_mps))
    times_s = np.arange(0.0, duration_s + output_step_s, output_step_s)

    solution = solve_ivp(
        _high_fidelity_rhs,
        t_span=(0.0, float(times_s[-1])),
        y0=y0,
        args=(epoch, include_j3, include_third_body),
        t_eval=times_s,
        rtol=1e-9,
        atol=1e-3,
    )
    if not solution.success:
        raise RuntimeError(f"High-fidelity propagation failed: {solution.message}")

    states = solution.y.T
    return pd.DataFrame(
        {
            "t_s": solution.t,
            "x_eci_m": states[:, 0],
            "y_eci_m": states[:, 1],
            "z_eci_m": states[:, 2],
            "vx_eci_mps": states[:, 3],
            "vy_eci_mps": states[:, 4],
            "vz_eci_mps": states[:, 5],
        }
    )


def argp_drift_deg_per_day(
    config: MissionConfig, inclination_deg: float, days: float = 30.0
) -> float:
    """Numeric secular argp drift at a given inclination (frozen-apsides check)."""

    orbit = replace(config.orbit, inclination_rad=math.radians(inclination_deg))
    scenario = replace(config, orbit=orbit)
    history = propagate_high_fidelity(
        scenario, duration_s=days * 86400.0, output_step_s=86400.0
    )
    day_index = history["t_s"].to_numpy() / 86400.0
    argps = np.array(
        [
            rv_to_classical_elements(
                row[["x_eci_m", "y_eci_m", "z_eci_m"]].to_numpy(),
                row[["vx_eci_mps", "vy_eci_mps", "vz_eci_mps"]].to_numpy(),
            )["argp_rad"]
            for _, row in history.iterrows()
        ]
    )
    unwrapped_deg = np.degrees(np.unwrap(argps))
    slope = float(np.polyfit(day_index, unwrapped_deg, 1)[0])
    return slope


def orbit_summary(config: MissionConfig) -> dict[str, float]:
    """Molniya orbit-physics summary for evidence and the dashboard."""

    orbit = config.orbit
    raan_rate, argp_rate = secular_rates_rad_s(
        orbit.semi_major_axis_m, orbit.eccentricity, orbit.inclination_rad
    )
    budget = station_keeping_delta_v(config)
    return {
        "critical_inclination_deg": math.degrees(CRITICAL_INCLINATION_RAD),
        "inclination_deg": math.degrees(orbit.inclination_rad),
        "analytic_argp_rate_deg_per_day": math.degrees(argp_rate) * 86400.0,
        "analytic_raan_rate_deg_per_day": math.degrees(raan_rate) * 86400.0,
        "station_keeping_delta_v_m_s_per_year": budget.delta_v_incl_m_s_per_year,
        "station_keeping_delta_v_5yr_m_s": budget.delta_v_5yr_m_s,
        "inclination_drift_deg_per_year": budget.inclination_drift_deg_per_year,
    }


@dataclass(frozen=True)
class StationKeepingBudget:
    inclination_drift_deg_per_year: float
    delta_v_incl_m_s_per_year: float
    delta_v_5yr_m_s: float
    note: str


def station_keeping_delta_v(config: MissionConfig, days: float = 60.0) -> StationKeepingBudget:
    """Order-of-magnitude luni-solar inclination station-keeping estimate.

    Inclination is corrected most cheaply at apogee, so
    ``dV = 2 v_apogee sin(di/2)`` per year. Argument of perigee is not budgeted
    because the critical inclination freezes it (see ``frozen_apsides_scan``).
    """

    history = propagate_high_fidelity(config, duration_s=days * 86400.0, output_step_s=86400.0)
    inclinations = np.array(
        [
            rv_to_classical_elements(
                row[["x_eci_m", "y_eci_m", "z_eci_m"]].to_numpy(),
                row[["vx_eci_mps", "vy_eci_mps", "vz_eci_mps"]].to_numpy(),
            )["i_rad"]
            for _, row in history.iterrows()
        ]
    )
    day_index = history["t_s"].to_numpy() / 86400.0
    incl_rate_rad_per_day = float(np.polyfit(day_index, inclinations, 1)[0])
    incl_drift_deg_per_year = abs(math.degrees(incl_rate_rad_per_day) * 365.25)

    a_m = config.orbit.semi_major_axis_m
    apogee_radius_m = config.orbit.apogee_radius_m
    v_apogee = math.sqrt(EARTH_MU_M3_S2 * (2.0 / apogee_radius_m - 1.0 / a_m))
    delta_v_per_year = 2.0 * v_apogee * math.sin(math.radians(incl_drift_deg_per_year) / 2.0)
    return StationKeepingBudget(
        inclination_drift_deg_per_year=incl_drift_deg_per_year,
        delta_v_incl_m_s_per_year=delta_v_per_year,
        delta_v_5yr_m_s=delta_v_per_year * config.spacecraft.design_lifetime_years,
        note="Luni-solar inclination maintenance at apogee; argp frozen at 63.4 deg.",
    )
