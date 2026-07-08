import pandas as pd
from lunalink.thermal import FACE_AREAS_M2, ThermalConfig, run_thermal


def _environment_table(
    *,
    duration_s: float = 3600.0,
    step_s: float = 60.0,
    solar_flux_w_m2: float = 1361.0,
    earth_ir_flux_w_m2: float = 180.0,
    albedo_flux_w_m2: float = 90.0,
    eclipse_flag: bool = False,
) -> pd.DataFrame:
    times = list(range(0, int(duration_s) + 1, int(step_s)))
    return pd.DataFrame(
        {
            "t_s": [float(t_s) for t_s in times],
            "eclipse_flag": [eclipse_flag] * len(times),
            "solar_flux_w_m2": [solar_flux_w_m2] * len(times),
            "earth_ir_flux_w_m2": [earth_ir_flux_w_m2] * len(times),
            "albedo_flux_w_m2": [albedo_flux_w_m2] * len(times),
            "x_eci_m": [7_000_000.0] * len(times),
            "y_eci_m": [float(t_s) for t_s in times],
            "z_eci_m": [0.0] * len(times),
            "vx_eci_mps": [0.0] * len(times),
            "vy_eci_mps": [7_500.0] * len(times),
            "vz_eci_mps": [0.0] * len(times),
            "sun_hat_x": [1.0] * len(times),
            "sun_hat_y": [0.0] * len(times),
            "sun_hat_z": [0.0] * len(times),
        }
    )


def test_box_face_areas_sum_to_13_square_meters():
    assert sum(FACE_AREAS_M2.values()) == 13.0


def test_black_coating_runs_hotter_than_white_under_sun():
    environment = _environment_table(duration_s=2.0 * 3600.0, earth_ir_flux_w_m2=0.0)

    _, white_summary = run_thermal(
        environment, power_w=0.0, config=ThermalConfig(coating="white")
    )
    _, black_summary = run_thermal(
        environment, power_w=0.0, config=ThermalConfig(coating="black")
    )

    assert black_summary["max_temp_k"] > white_summary["max_temp_k"] + 20.0


def test_internal_dissipation_raises_internal_temperature():
    environment = _environment_table(
        duration_s=2.0 * 3600.0,
        solar_flux_w_m2=0.0,
        earth_ir_flux_w_m2=0.0,
        albedo_flux_w_m2=0.0,
        eclipse_flag=True,
    )

    _, unpowered_summary = run_thermal(environment, power_w=0.0)
    _, powered_summary = run_thermal(environment, power_w=300.0)

    assert powered_summary["final_internal_temp_k"] > unpowered_summary["final_internal_temp_k"]


def test_temperatures_stay_positive():
    environment = _environment_table(
        duration_s=6.0 * 3600.0,
        solar_flux_w_m2=0.0,
        earth_ir_flux_w_m2=0.0,
        albedo_flux_w_m2=0.0,
        eclipse_flag=True,
    )

    timeseries, summary = run_thermal(environment, power_w=0.0)

    assert summary["min_temp_k"] > 0.0
    assert timeseries.filter(like="_k").min().min() > 0.0


def test_component_limit_flags_appear():
    environment = _environment_table(duration_s=600.0)

    timeseries, summary = run_thermal(environment)

    expected_flags = {
        "internal_cold_limit_flag",
        "internal_hot_limit_flag",
        "external_cold_limit_flag",
        "external_hot_limit_flag",
        "component_limit_flag",
    }
    assert expected_flags.issubset(timeseries.columns)
    assert set(summary["component_limit_flags"]) == {
        "internal_cold",
        "internal_hot",
        "external_cold",
        "external_hot",
    }
    assert "worst_operating_margin_k" in summary


def test_time_varying_power_profile_changes_summary():
    environment = _environment_table(duration_s=120.0, step_s=60.0)
    power_profile = pd.Series([100.0, 200.0, 300.0])

    timeseries, summary = run_thermal(environment, power_w=power_profile)

    assert timeseries["power_w"].tolist() == [100.0, 200.0, 300.0]
    assert summary["average_power_w"] == 200.0


def test_per_face_coatings_are_recorded():
    environment = _environment_table(duration_s=60.0, step_s=60.0)
    config = ThermalConfig(face_coatings={"z_neg": "OSR/FEP", "z_pos": "MLI"})

    timeseries, summary = run_thermal(environment, config=config)

    assert timeseries["coating_z_neg"].iloc[0] == "OSR/FEP"
    assert summary["face_coatings"]["z_neg"] == "OSR/FEP"
