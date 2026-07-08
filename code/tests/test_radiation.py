"""Tests for the radiation-belt dose and solar-array degradation model.

Sanity ranges are anchored to published values: a belt-crossing HEO/GEO orbit
sees ~10-30 krad(Si)/yr behind ~100 mil Al, and triple-junction arrays lose
order ~5-15 % over a 5-year mission.
"""

from __future__ import annotations

import numpy as np
from lunalink import radiation as rad
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.environment import build_environment_table


def _environment():
    base = default_mission_config()
    config = MissionConfig(
        orbit=base.orbit, spacecraft=base.spacecraft, ground_station=base.ground_station,
        simulation=SimulationConfig(epoch_utc=base.simulation.epoch_utc,
                                    duration_s=36 * 3600.0, output_step_s=120.0),
    )
    return build_environment_table(config, include_j2=True)


def test_mcilwain_l_low_at_perigee_high_at_apogee() -> None:
    env = _environment()
    l_shell = rad.mcilwain_l(env)
    assert l_shell.min() < 2.0  # perigee is inside the inner belt region
    assert l_shell.max() > 6.0  # apogee reaches the outer belt / beyond
    assert np.all(l_shell > 1.0)


def test_trapped_flux_peaks_in_outer_belt() -> None:
    l_grid = np.linspace(1.0, 9.0, 200)
    flux = rad.trapped_electron_flux(l_grid)
    peak_l = l_grid[int(np.argmax(flux))]
    assert 3.5 <= peak_l <= 5.5
    assert rad.trapped_electron_flux(np.array([10.0]))[0] == 0.0


def test_array_remaining_power_is_monotonic_and_bounded() -> None:
    assert rad.array_remaining_power_factor(0.0) == 1.0
    assert rad.array_remaining_power_factor(1e14) < 1.0
    assert rad.array_remaining_power_factor(5e15) < rad.array_remaining_power_factor(1e14)


def test_radiation_summary_matches_published_orders_of_magnitude() -> None:
    summary = rad.radiation_summary(_environment(), years=5.0)
    assert 5.0 <= summary.annual_dose_krad_si_estimate <= 60.0
    assert 0.80 <= summary.array_remaining_power_5yr <= 0.98
    assert summary.peak_l_shell > 6.0
    assert 0.0 < summary.fraction_in_belts < 1.0
    assert summary.fluence_5yr_1mev_e_cm2 > summary.annual_fluence_1mev_e_cm2
