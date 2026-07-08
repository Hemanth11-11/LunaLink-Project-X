"""Tests for the high-fidelity orbit analysis, anchored to Orekit/SPICE numbers.

Reference values from an executed Orekit 13.1 cross-check (see
``outputs/baseline/external_validation/spice_orekit_crosscheck.md``):
argp drift 0.293 deg/day at i=45 deg and 0.004 deg/day at i=63.4 deg.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from lunalink import orbit_analysis as oa
from lunalink.config import default_mission_config
from lunalink.constants import EARTH_J3, EARTH_MU_M3_S2, EARTH_RADIUS_M
from lunalink.orbit import j3_acceleration, orbital_elements_to_state


def _j3_potential(r: np.ndarray) -> float:
    radius = np.linalg.norm(r)
    z = r[2]
    return EARTH_MU_M3_S2 * EARTH_J3 * EARTH_RADIUS_M**3 * 0.5 * (
        5.0 * z**3 / radius**7 - 3.0 * z / radius**5
    )


def test_j3_acceleration_matches_potential_gradient() -> None:
    r = np.array([9.0e6, 3.0e6, 5.0e6])
    grad = np.zeros(3)
    step = 1.0
    for k in range(3):
        rp, rm = r.copy(), r.copy()
        rp[k] += step
        rm[k] -= step
        grad[k] = (_j3_potential(rp) - _j3_potential(rm)) / (2.0 * step)
    analytic = j3_acceleration(r)
    assert np.linalg.norm(analytic + grad) / np.linalg.norm(grad) < 1e-6


def test_critical_inclination_is_63p43_deg() -> None:
    assert math.degrees(oa.CRITICAL_INCLINATION_RAD) == pytest.approx(63.4349, abs=1e-3)


def test_secular_argp_rate_vanishes_at_critical_inclination() -> None:
    orbit = default_mission_config().orbit
    _, argp_rate = oa.secular_rates_rad_s(
        orbit.semi_major_axis_m, orbit.eccentricity, oa.CRITICAL_INCLINATION_RAD
    )
    assert abs(math.degrees(argp_rate) * 86400.0) < 1e-6


def test_frozen_apsides_scan_crosses_zero_near_critical() -> None:
    scan = oa.frozen_apsides_scan(default_mission_config().orbit)
    zero_crossing = scan.iloc[scan["argp_rate_deg_per_day"].abs().idxmin()]
    assert abs(zero_crossing["inclination_deg"] - 63.43) < 1.0


def test_numeric_argp_drift_matches_orekit() -> None:
    config = default_mission_config()
    drift_45 = oa.argp_drift_deg_per_day(config, 45.0, days=20.0)
    drift_63 = oa.argp_drift_deg_per_day(config, 63.4, days=20.0)
    assert 0.25 < drift_45 < 0.33  # Orekit 0.293 deg/day
    assert abs(drift_63) < 0.02  # Orekit 0.004 deg/day: apsides frozen
    assert abs(drift_63) < 0.1 * abs(drift_45)


def test_rv_to_classical_round_trips_config_elements() -> None:
    orbit = default_mission_config().orbit
    state = orbital_elements_to_state(orbit)
    elements = oa.rv_to_classical_elements(state.r_eci_m, state.v_eci_mps)
    assert elements["a_m"] == pytest.approx(orbit.semi_major_axis_m, rel=1e-9)
    assert elements["e"] == pytest.approx(orbit.eccentricity, rel=1e-6)
    assert elements["i_rad"] == pytest.approx(orbit.inclination_rad, abs=1e-9)
    assert elements["argp_rad"] == pytest.approx(orbit.argument_of_perigee_rad, abs=1e-6)


def test_station_keeping_budget_is_small_and_positive() -> None:
    budget = oa.station_keeping_delta_v(default_mission_config(), days=40.0)
    assert budget.delta_v_incl_m_s_per_year > 0.0
    assert budget.delta_v_5yr_m_s < 100.0  # Molniya inclination SK is tens of m/s
