import json
from pathlib import Path

import pandas as pd
from lunalink.environment import build_environment_table
from lunalink.reporting import build_markdown_report
from main_gui import build_gui_config, build_orbit_figure, build_spacecraft_figure


def test_build_gui_config_uses_36_hour_mission():
    config = build_gui_config(output_step_s=600.0)

    assert config.simulation.duration_s == 36.0 * 3600.0
    assert config.simulation.output_step_s == 600.0


def test_gui_3d_figures_build_from_mission_data():
    config = build_gui_config(output_step_s=600.0)
    environment = build_environment_table(config, include_j2=False)

    spacecraft_figure = build_spacecraft_figure(
        {
            "spacecraft": {
                "length_x_m": config.spacecraft.length_x_m,
                "length_y_m": config.spacecraft.length_y_m,
                "length_z_m": config.spacecraft.length_z_m,
            }
        }
    )
    orbit_figure = build_orbit_figure(environment, sample_stride=2)

    assert len(spacecraft_figure.data) >= 4
    assert len(orbit_figure.data) >= 2


def test_build_markdown_report(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "run_manifest.json").write_text(
        json.dumps(
            {"mode": "quick", "include_j2": True, "critical_failures": False, "figures": {}}
        ),
        encoding="utf-8",
    )
    (evidence / "subsystem_summaries.json").write_text(
        json.dumps({"eps": {"min_soc": 0.5}, "ttc": {"xband": "ok"}}),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "name": "simulation_duration_h",
                "status": "pass",
                "value": 36.0,
                "criterion": "Must be at least 36 h",
                "source_module": "environment",
            }
        ]
    ).to_csv(evidence / "validation_metrics.csv", index=False)

    output = build_markdown_report(evidence, tmp_path / "report.md")

    assert output == Path(tmp_path / "report.md")
    text = output.read_text(encoding="utf-8")
    assert "LunaLink Engineering Simulation Report" in text
    assert "simulation_duration_h" in text
