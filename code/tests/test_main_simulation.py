from pathlib import Path

from main_simulation import main


def test_main_simulation_quick_writes_evidence(tmp_path, monkeypatch):
    output_dir = tmp_path / "quick"
    monkeypatch.setattr(
        "sys.argv",
        ["main_simulation.py", "--quick", "--two-body", "--out", str(output_dir)],
    )

    assert main() == 0
    assert (output_dir / "run_manifest.json").exists()
    assert (output_dir / "assumptions.json").exists()
    assert (output_dir / "subsystem_summaries.json").exists()
    assert (output_dir / "mission_timeseries.csv").exists()
    assert (output_dir / "eps_timeseries.csv").exists()
    assert (output_dir / "thermal_timeseries.csv").exists()
    assert (output_dir / "adcs_timeseries.csv").exists()
    assert (output_dir / "ttc_timeseries.csv").exists()
    assert (output_dir / "trade_results.csv").exists()
    assert (output_dir / "lhs_samples.csv").exists()
    assert (output_dir / "monte_carlo_samples.csv").exists()
    assert (output_dir / "formula_traceability.csv").exists()
    assert (output_dir / "scenario_exports" / "LunaLink_GMAT_scenario.script").exists()
    assert (output_dir / "scenario_exports" / "LunaLink_Orekit_scenario.json").exists()
    assert (
        output_dir / "scenario_exports" / "LunaLink_external_validation_recipe.md"
    ).exists()
    assert (output_dir / "figures" / "pareto_eps_trade.png").exists()
    assert (output_dir / "validation_metrics.csv").exists()
    assert Path(output_dir / "validation_metrics.csv").read_text(encoding="utf-8")
