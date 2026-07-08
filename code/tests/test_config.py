from lunalink.config import default_mission_config
from lunalink.constants import RAD2DEG


def test_default_orbit_matches_brief_altitudes_and_period():
    config = default_mission_config()

    assert config.orbit.perigee_altitude_m == 500_000.0
    assert config.orbit.apogee_altitude_m == 36_000_000.0
    assert round(config.orbit.inclination_rad * RAD2DEG, 1) == 63.4
    assert abs(config.orbit.period_s / 3600.0 - 10.6845) < 0.001


def test_default_config_meets_minimum_duration():
    config = default_mission_config()

    assert config.simulation.duration_s >= 36.0 * 3600.0
    assert config.validation_messages() == []

