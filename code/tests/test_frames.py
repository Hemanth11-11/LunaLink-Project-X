import numpy as np
from lunalink.config import default_mission_config
from lunalink.constants import EARTH_RADIUS_M, EARTH_ROT_RATE_RAD_S
from lunalink.frames import (
    ecef_to_geodetic_lat_lon_alt,
    eci_to_ecef_matrix,
    enu_basis,
    geodetic_to_ecef,
    topocentric_az_el_range,
)


def test_equator_greenwich_station_points_along_x_axis():
    station = geodetic_to_ecef(0.0, 0.0, 0.0)

    assert np.allclose(station, np.array([EARTH_RADIUS_M, 0.0, 0.0]), atol=1e-6)


def test_overhead_target_has_near_zenith_elevation():
    config = default_mission_config()
    station = geodetic_to_ecef(
        config.ground_station.latitude_rad,
        config.ground_station.longitude_rad,
        config.ground_station.altitude_m,
    )
    _, _, up = enu_basis(config.ground_station.latitude_rad, config.ground_station.longitude_rad)
    target = station + 100_000.0 * up

    _, elevation_rad, range_m = topocentric_az_el_range(
        target,
        station,
        config.ground_station.latitude_rad,
        config.ground_station.longitude_rad,
    )

    assert range_m > 0.0
    assert np.isclose(elevation_rad, np.pi / 2.0, atol=1e-12)


def test_geodetic_round_trip_for_ground_station():
    config = default_mission_config()
    station = geodetic_to_ecef(
        config.ground_station.latitude_rad,
        config.ground_station.longitude_rad,
        config.ground_station.altitude_m,
    )

    latitude_rad, longitude_rad, altitude_m = ecef_to_geodetic_lat_lon_alt(station)

    assert np.isclose(latitude_rad, config.ground_station.latitude_rad, atol=1e-12)
    assert np.isclose(longitude_rad, config.ground_station.longitude_rad, atol=1e-12)
    assert np.isclose(altitude_m, config.ground_station.altitude_m, atol=1e-6)


def test_eci_to_ecef_rotation_uses_passive_earth_fixed_sign():
    quarter_turn_s = 0.5 * np.pi / EARTH_ROT_RATE_RAD_S
    inertial_x = np.array([1.0, 0.0, 0.0])

    fixed = eci_to_ecef_matrix(quarter_turn_s) @ inertial_x

    assert np.allclose(fixed, np.array([0.0, -1.0, 0.0]), atol=1e-12)
