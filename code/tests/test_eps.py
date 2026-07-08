import numpy as np
import pandas as pd
from lunalink.eps import EpsConfig, run_eps


def environment_rows(
    t_s: list[float],
    *,
    eclipse: bool = False,
    solar_flux_w_m2: float = 1361.0,
    contact: bool = False,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "t_s": t_s,
            "eclipse_flag": [eclipse] * len(t_s),
            "solar_flux_w_m2": [0.0 if eclipse else solar_flux_w_m2] * len(t_s),
            "sun_hat_x": [1.0] * len(t_s),
            "sun_hat_y": [0.0] * len(t_s),
            "sun_hat_z": [0.0] * len(t_s),
            "gs_contact_flag": [contact] * len(t_s),
        }
    )


def test_eclipse_has_no_solar_generation_and_discharges_battery():
    config = EpsConfig(peak_duty_cycle=0.0)
    environment = environment_rows([0.0, 60.0, 120.0], eclipse=True)

    timeseries, summary = run_eps(environment, config)

    assert timeseries["solar_power_w"].eq(0.0).all()
    assert timeseries["load_power_w"].eq(config.safe_load_w).all()
    assert timeseries["battery_soc"].iloc[-1] < config.initial_soc
    assert summary["eclipse_duration_s"] == 120.0


def test_positive_energy_balance_raises_soc_in_sunlight():
    config = EpsConfig(peak_duty_cycle=0.0, initial_soc=0.4)
    environment = environment_rows([0.0, 600.0, 1_200.0], eclipse=False)

    timeseries, summary = run_eps(environment, config)

    assert summary["net_energy_j"] > 0.0
    assert timeseries["battery_soc"].iloc[-1] > config.initial_soc
    assert summary["average_generation_w"] > summary["average_load_w"]


def test_fixed_array_uses_cosine_incidence():
    config = EpsConfig(peak_duty_cycle=0.0, array_pointing_mode="fixed_eci")
    aligned = environment_rows([0.0, 60.0], eclipse=False)
    off_axis = aligned.copy()
    off_axis["sun_hat_x"] = 0.0
    off_axis["sun_hat_y"] = 1.0

    aligned_timeseries, _ = run_eps(aligned, config)
    off_axis_timeseries, _ = run_eps(off_axis, config)

    assert aligned_timeseries["array_incidence_factor"].iloc[0] == 1.0
    assert off_axis_timeseries["array_incidence_factor"].iloc[0] == 0.0
    assert off_axis_timeseries["solar_power_w"].iloc[0] == 0.0


def test_soc_is_clamped_to_physical_bounds():
    charge_config = EpsConfig(
        peak_duty_cycle=0.0,
        initial_soc=0.99,
        safe_load_w=100.0,
        nominal_load_w=100.0,
    )
    sunny_environment = environment_rows([0.0, 7_200.0], eclipse=False)
    charge_timeseries, _ = run_eps(sunny_environment, charge_config)

    discharge_config = EpsConfig(
        peak_duty_cycle=1.0,
        battery_capacity_kwh=0.05,
        initial_soc=0.1,
    )
    eclipse_environment = environment_rows([0.0, 3_600.0], eclipse=True)
    discharge_timeseries, _ = run_eps(eclipse_environment, discharge_config)

    assert charge_timeseries["battery_soc"].between(0.0, 1.0).all()
    assert discharge_timeseries["battery_soc"].between(0.0, 1.0).all()
    assert np.isclose(charge_timeseries["battery_soc"].max(), 1.0)
    assert np.isclose(discharge_timeseries["battery_soc"].min(), 0.0)


def test_increasing_peak_duty_cycle_increases_load_and_reduces_soc_margin():
    environment = environment_rows([0.0, 600.0, 1_200.0, 1_800.0, 2_400.0], eclipse=True)
    low_duty_config = EpsConfig(peak_duty_cycle=0.0)
    high_duty_config = EpsConfig(peak_duty_cycle=0.75)

    low_duty_timeseries, low_duty_summary = run_eps(environment, low_duty_config)
    high_duty_timeseries, high_duty_summary = run_eps(environment, high_duty_config)

    assert high_duty_summary["average_load_w"] > low_duty_summary["average_load_w"]
    assert high_duty_timeseries["battery_soc"].min() <= low_duty_timeseries["battery_soc"].min()
