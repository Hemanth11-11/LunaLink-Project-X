import json

import pandas as pd
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.environment import build_environment_table
from lunalink.io import write_dataframe, write_json
from lunalink.validation import (
    has_critical_failures,
    metrics_to_dataframe,
    validate_environment_table,
    validate_subsystem_summaries,
)


def test_environment_validation_metrics_pass_for_short_valid_baseline():
    config = MissionConfig(
        simulation=SimulationConfig(duration_s=36.0 * 3600.0, output_step_s=600.0)
    )
    table = build_environment_table(config, include_j2=False)
    metrics = validate_environment_table(config, table)
    metrics_df = metrics_to_dataframe(metrics)

    assert not has_critical_failures(metrics)
    assert {"name", "value", "criterion", "status", "severity", "source_module"}.issubset(
        metrics_df.columns
    )


def test_io_writes_json_and_csv(tmp_path):
    config = default_mission_config()
    json_path = write_json(tmp_path / "assumptions.json", {"mission": config})
    csv_path = write_dataframe(tmp_path / "table.csv", pd.DataFrame({"a": [1], "b": [2]}))

    written = json.loads(json_path.read_text(encoding="utf-8"))

    assert written["mission"]["spacecraft"]["mass_kg"] == 500.0
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "a,b"


def test_subsystem_summary_validation_catches_major_margins():
    metrics = validate_subsystem_summaries(
        {
            "eps": {
                "min_soc": 0.5,
                "unserved_energy_j": 0.0,
                "array_eol_power_w": 1300.0,
                "peak_load_w": 1200.0,
                "average_load_w": 900.0,
            },
            "thermal": {"component_limit_flag": False},
            "adcs": {"final_angular_speed_deg_s": 0.01, "wheel_saturated": False},
            "ttc": {
                "xband_min_margin_db": 5.0,
                "uhf_min_margin_db": 4.0,
                "xband_data_rate_bps": 100.0e6,
            },
        }
    )

    assert not has_critical_failures(metrics)
    assert {metric.source_module for metric in metrics} == {"eps", "thermal", "adcs", "ttc"}
