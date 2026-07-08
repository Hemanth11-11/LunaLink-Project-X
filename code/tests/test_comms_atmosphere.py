"""Tests for the ITU-R atmospheric loss, CCSDS coding and Doppler helpers."""

from __future__ import annotations

from lunalink.comms_atmosphere import (
    ccsds_coding_gain_db,
    comms_atmosphere_summary,
    doppler_shift_hz,
    slant_attenuation_db,
)
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.constants import SPEED_OF_LIGHT_M_S
from lunalink.environment import build_environment_table


def _environment():
    base = default_mission_config()
    config = MissionConfig(
        orbit=base.orbit, spacecraft=base.spacecraft, ground_station=base.ground_station,
        simulation=SimulationConfig(epoch_utc=base.simulation.epoch_utc,
                                    duration_s=36 * 3600.0, output_step_s=300.0),
    )
    return build_environment_table(config, include_j2=True)


def test_ccsds_coding_gain_positive_for_coded_scheme() -> None:
    assert ccsds_coding_gain_db("rs_conv_concatenated") == 8.0
    assert ccsds_coding_gain_db("uncoded_bpsk") == 0.0
    assert ccsds_coding_gain_db("turbo_r1_6") > 9.0


def test_doppler_shift_scales_with_range_rate() -> None:
    freq = 8.4e9
    shift = doppler_shift_hz(freq, 3000.0)
    assert shift < 0.0  # receding lowers frequency
    assert abs(abs(shift) - freq * 3000.0 / SPEED_OF_LIGHT_M_S) < 1.0


def test_slant_attenuation_decreases_with_elevation() -> None:
    low = slant_attenuation_db(5.0, 48.07, 11.65, 8.4, 3.0)
    high = slant_attenuation_db(90.0, 48.07, 11.65, 8.4, 3.0)
    assert low > high > 0.0


def test_comms_summary_matches_physical_ranges() -> None:
    summary = comms_atmosphere_summary(_environment(), 48.07, 11.65)
    assert 1.0 <= summary["atmos_loss_5deg_db"] <= 6.0
    assert summary["atmos_loss_5deg_db"] > summary["atmos_loss_zenith_db"]
    assert summary["ccsds_coding_gain_db"] >= 3.0
    assert 10.0 <= summary["max_doppler_khz"] <= 200.0
