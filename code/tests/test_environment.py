import numpy as np
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.constants import EARTH_RADIUS_M
from lunalink.environment import (
    approximate_sun_hat_eci,
    build_environment_table,
    in_cylindrical_eclipse,
    parse_epoch_utc,
    simple_dipole_field_ecef_t,
)


def test_cylindrical_eclipse_geometry():
    sun_hat = np.array([1.0, 0.0, 0.0])

    assert in_cylindrical_eclipse(np.array([-EARTH_RADIUS_M - 500_000.0, 0.0, 0.0]), sun_hat)
    assert not in_cylindrical_eclipse(
        np.array([EARTH_RADIUS_M + 500_000.0, 0.0, 0.0]), sun_hat
    )
    assert not in_cylindrical_eclipse(
        np.array([-EARTH_RADIUS_M - 500_000.0, 2.0 * EARTH_RADIUS_M, 0.0]), sun_hat
    )


def test_sun_vector_is_unit_length():
    epoch = parse_epoch_utc(default_mission_config().simulation.epoch_utc)
    sun_hat = approximate_sun_hat_eci(epoch, 0.0)

    assert np.isclose(np.linalg.norm(sun_hat), 1.0)


def test_simple_dipole_field_is_earth_fixed():
    r_ecef_m = np.array([EARTH_RADIUS_M + 500_000.0, 0.0, 0.0])

    first = simple_dipole_field_ecef_t(r_ecef_m)
    second = simple_dipole_field_ecef_t(r_ecef_m)

    assert np.allclose(first, second)


def test_environment_table_has_contact_and_environment_columns():
    base = default_mission_config()
    config = MissionConfig(
        simulation=SimulationConfig(duration_s=2.0 * 3600.0, output_step_s=300.0)
    )
    table = build_environment_table(config, include_j2=False)

    required = {
        "t_s",
        "x_eci_m",
        "x_ecef_m",
        "lat_rad",
        "lon_rad",
        "eclipse_flag",
        "solar_flux_w_m2",
        "gs_range_m",
        "gs_elevation_rad",
        "gs_contact_flag",
        "moon_range_m",
        "moon_occulted_flag",
        "b_eci_x_t",
        "atmospheric_density_kg_m3",
    }

    assert required.issubset(table.columns)
    assert len(table) > 1
    assert table["t_s"].iloc[-1] == config.simulation.duration_s
    assert table.loc[table["gs_contact_flag"], "gs_elevation_rad"].ge(
        base.ground_station.min_elevation_rad
    ).all()
