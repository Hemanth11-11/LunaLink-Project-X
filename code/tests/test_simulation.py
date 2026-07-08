from lunalink.config import MissionConfig, SimulationConfig
from lunalink.simulation import run_mission
from lunalink.validation import has_critical_failures


def test_run_mission_returns_all_subsystems_for_coarse_baseline():
    config = MissionConfig(
        simulation=SimulationConfig(duration_s=36.0 * 3600.0, output_step_s=900.0)
    )

    results = run_mission(config, include_j2=False)

    assert not has_critical_failures(results.validation_metrics)
    assert len(results.environment) == len(results.eps)
    assert len(results.environment) == len(results.thermal)
    assert len(results.environment) == len(results.adcs)
    assert len(results.environment) == len(results.ttc)
    assert results.summaries["eps"]["min_soc"] >= 0.0
    assert results.summaries["thermal"]["min_temp_k"] > 0.0
    assert results.summaries["adcs"]["final_angular_speed_deg_s"] >= 0.0
    assert results.summaries["ttc"]["total_data_volume_bits"] >= 0.0

