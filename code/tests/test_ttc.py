import math

import numpy as np
import pandas as pd
import pytest
from lunalink.ttc import (
    LinkConfig,
    antenna_gain_dbi,
    contact_windows,
    free_space_path_loss_db,
    run_ttc,
    threshold_windows,
)


def _environment_table(
    times_s: list[float],
    gs_ranges_m: list[float],
    gs_contacts: list[bool],
    moon_occulted: list[bool] | None = None,
) -> pd.DataFrame:
    if moon_occulted is None:
        moon_occulted = [False] * len(times_s)
    return pd.DataFrame(
        {
            "t_s": times_s,
            "gs_range_m": gs_ranges_m,
            "gs_elevation_rad": [0.2 if flag else -0.1 for flag in gs_contacts],
            "gs_contact_flag": gs_contacts,
            "moon_range_m": [384_400_000.0] * len(times_s),
            "moon_occulted_flag": moon_occulted,
        }
    )


def test_free_space_path_loss_slopes_with_range_and_frequency():
    base = free_space_path_loss_db(1_000_000.0, 1.0e9)

    doubled_range = free_space_path_loss_db(2_000_000.0, 1.0e9)
    ten_x_frequency = free_space_path_loss_db(1_000_000.0, 10.0e9)

    assert np.isclose(doubled_range - base, 20.0 * math.log10(2.0))
    assert np.isclose(ten_x_frequency - base, 20.0)


def test_antenna_gain_formula_matches_baseline_sanity_values():
    spacecraft_gain = antenna_gain_dbi(8.4e9, 0.6, 0.60)
    ground_gain = antenna_gain_dbi(8.4e9, 3.0, 0.62)
    doubled_diameter_gain = antenna_gain_dbi(8.4e9, 1.2, 0.60)

    assert np.isclose(spacecraft_gain, 32.2, atol=0.2)
    assert np.isclose(ground_gain, 46.4, atol=0.2)
    assert np.isclose(doubled_diameter_gain - spacecraft_gain, 20.0 * math.log10(2.0))


def test_antenna_efficiency_must_be_physical():
    with pytest.raises(ValueError):
        antenna_gain_dbi(8.4e9, 0.6, 1.2)


def test_link_config_rejects_negative_losses():
    with pytest.raises(ValueError):
        LinkConfig(
            name="bad",
            frequency_hz=1.0e9,
            data_rate_bps=1.0e6,
            tx_power_w=10.0,
            system_noise_temp_k=300.0,
            required_ebn0_db=5.0,
            propagation_loss_db=-1.0,
        )


def test_contact_windows_convert_sampled_flags_to_durations():
    windows = contact_windows([0.0, 10.0, 20.0, 35.0], [False, True, True, False])

    assert windows == [{"start_s": 10.0, "end_s": 35.0, "duration_s": 25.0}]


def test_threshold_windows_interpolate_crossings():
    windows = threshold_windows([0.0, 10.0, 20.0, 30.0], [-1.0, 1.0, 1.0, -1.0], 0.0)

    assert windows == [{"start_s": 5.0, "end_s": 25.0, "duration_s": 20.0}]


def test_xband_availability_requires_contact_and_margin():
    env = _environment_table(
        times_s=[0.0, 10.0, 20.0],
        gs_ranges_m=[1_000_000.0, 1_000_000.0, 1.0e12],
        gs_contacts=[True, False, True],
    )

    timeseries, _ = run_ttc(env)

    assert timeseries["xband_available_flag"].tolist() == [True, False, False]
    assert timeseries.loc[1, "xband_margin_ok_flag"]
    assert not timeseries.loc[2, "xband_margin_ok_flag"]


def test_xband_data_volume_integrates_active_rate_over_sample_intervals():
    env = _environment_table(
        times_s=[0.0, 10.0, 25.0],
        gs_ranges_m=[1_000_000.0, 1_000_000.0, 1_000_000.0],
        gs_contacts=[True, True, False],
    )

    timeseries, summary = run_ttc(env)

    expected_bits = 100.0e6 * 25.0
    assert timeseries["xband_volume_bits"].tolist() == [1.0e9, 1.5e9, 0.0]
    assert np.isclose(timeseries["xband_cumulative_volume_bits"].iloc[-1], expected_bits)
    assert np.isclose(summary["xband_data_volume_bits"], expected_bits)
    assert summary["xband_refined_contact_windows"][0]["start_s"] == 0.0
    assert (
        summary["end_to_end_relay_volume_bits"]
        <= summary["aggregate_independent_link_volume_bits"]
    )


def test_link_budget_columns_are_exported():
    env = _environment_table(
        times_s=[0.0, 10.0],
        gs_ranges_m=[1_000_000.0, 1_000_000.0],
        gs_contacts=[True, True],
    )

    timeseries, _ = run_ttc(env)

    expected = {
        "xband_eirp_dbw",
        "xband_g_over_t_db_per_k",
        "xband_carrier_power_dbw",
        "xband_noise_density_dbw_hz",
        "xband_required_ebn0_db",
    }
    assert expected.issubset(timeseries.columns)
