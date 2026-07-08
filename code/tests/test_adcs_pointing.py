"""Tests for the closed-loop PD sun-pointing controller."""

from __future__ import annotations

from lunalink.adcs import SunPointingConfig, run_sun_pointing
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.environment import build_environment_table


def _environment(duration_h: float = 12.0):
    base = default_mission_config()
    config = MissionConfig(
        orbit=base.orbit, spacecraft=base.spacecraft, ground_station=base.ground_station,
        simulation=SimulationConfig(epoch_utc=base.simulation.epoch_utc,
                                    duration_s=duration_h * 3600.0, output_step_s=600.0),
    )
    return build_environment_table(config, include_j2=False)


def test_sun_pointing_converges_and_holds() -> None:
    _, summary = run_sun_pointing(_environment())
    assert summary["initial_pointing_error_deg"] > 20.0
    assert summary["final_pointing_error_deg"] < 1.0
    assert summary["settled_max_pointing_error_deg"] < summary["settle_error_deg"]
    assert summary["pointing_requirement_met"] is True


def test_sun_pointing_wheel_momentum_and_quaternion_bounded() -> None:
    config = default_mission_config()
    _, summary = run_sun_pointing(_environment())
    assert summary["max_wheel_momentum_nms"] < config.spacecraft.mass_kg  # comfortably bounded
    assert summary["max_q_norm_error"] < 1e-9


def test_sun_pointing_respects_target_axis() -> None:
    pointing = SunPointingConfig(target_body_axis=(1.0, 0.0, 0.0))
    timeseries, summary = run_sun_pointing(_environment(), pointing=pointing)
    assert summary["final_pointing_error_deg"] < 1.0
    assert "pointing_error_deg" in timeseries.columns
