"""Headless LunaLink simulation entry point."""

from __future__ import annotations

import argparse
import os
from dataclasses import asdict
from pathlib import Path

import pandas as pd
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.exporters import write_scenario_exports
from lunalink.io import ensure_directory, write_dataframe, write_json
from lunalink.plotting import save_basic_figures
from lunalink.simulation import run_mission
from lunalink.trades import eps_pareto_grid, latin_hypercube_samples, monte_carlo_samples
from lunalink.validation import has_critical_failures, metrics_to_dataframe

TRACEABILITY_ROWS = [
    {
        "requirement_id": "REQ-MIS-001",
        "formula_id": "F-ORB-001,F-ORB-002,F-ORB-003,F-ORB-004",
        "reference": "Vallado; NASA Systems Engineering Handbook",
        "implementation_path": "code/lunalink/orbit.py; code/lunalink/config.py",
        "test_path": "code/tests/test_orbit.py; code/tests/test_simulation.py",
        "validation_metric": (
            "fixed_altitude_orbit_period_h; minimum_altitude_km; maximum_altitude_km"
        ),
        "evidence_artifact": "validation_metrics.csv; mission_timeseries.csv",
    },
    {
        "requirement_id": "REQ-MIS-003",
        "formula_id": "F-GEO-001,F-FRAME-001",
        "reference": "Vallado; WGS84 geodetic station geometry",
        "implementation_path": "code/lunalink/frames.py; code/lunalink/environment.py",
        "test_path": "code/tests/test_frames.py; code/tests/test_ttc.py",
        "validation_metric": "minimum_contact_elevation_rad",
        "evidence_artifact": "mission_timeseries.csv; ttc_timeseries.csv",
    },
    {
        "requirement_id": "REQ-EPS-001",
        "formula_id": "F-EPS-001,F-EPS-002",
        "reference": "NASA SmallSat SOA Power; Wertz SMAD",
        "implementation_path": "code/lunalink/eps.py",
        "test_path": "code/tests/test_eps.py",
        "validation_metric": (
            "eps_minimum_state_of_charge; eps_unserved_energy_j; eps_array_eol_power_w"
        ),
        "evidence_artifact": "eps_timeseries.csv; validation_metrics.csv",
    },
    {
        "requirement_id": "REQ-TCS-001,REQ-TCS-002",
        "formula_id": "F-TCS-001,F-TCS-002",
        "reference": "Gilmore Spacecraft Thermal Control Handbook; NASA SmallSat SOA Thermal",
        "implementation_path": "code/lunalink/thermal.py",
        "test_path": "code/tests/test_thermal.py",
        "validation_metric": "thermal_component_limit_flag; thermal_worst_operating_margin_k",
        "evidence_artifact": "thermal_timeseries.csv; validation_metrics.csv",
    },
    {
        "requirement_id": "REQ-ADCS-001",
        "formula_id": "F-ADCS-001,F-ADCS-002,F-ADCS-003",
        "reference": "Wertz SMAD; NASA SmallSat SOA GNC",
        "implementation_path": "code/lunalink/adcs.py",
        "test_path": "code/tests/test_adcs.py",
        "validation_metric": "adcs_final_angular_speed_deg_s; adcs_wheel_saturated",
        "evidence_artifact": "adcs_timeseries.csv; validation_metrics.csv",
    },
    {
        "requirement_id": "REQ-TTC-001,REQ-TTC-002",
        "formula_id": "F-TTC-001,F-TTC-002,F-TTC-003",
        "reference": "CCSDS RF recommendations; JPL DESCANSO",
        "implementation_path": "code/lunalink/ttc.py",
        "test_path": "code/tests/test_ttc.py",
        "validation_metric": (
            "ttc_xband_min_margin_db; ttc_uhf_min_margin_db; ttc_xband_data_rate_bps"
        ),
        "evidence_artifact": "ttc_timeseries.csv; validation_metrics.csv",
    },
    {
        "requirement_id": "REQ-TRADE-001",
        "formula_id": "F-TRADE-001",
        "reference": "Design of experiments; Latin Hypercube sampling literature",
        "implementation_path": "code/lunalink/trades.py",
        "test_path": "code/tests/test_trades.py",
        "validation_metric": "reproducible fixed-seed samples",
        "evidence_artifact": "lhs_samples.csv; monte_carlo_samples.csv",
    },
    {
        "requirement_id": "REQ-XCHK-001",
        "formula_id": "F-ORB-001,F-GEO-001",
        "reference": "GMAT/Orekit independent astrodynamics correlation workflow",
        "implementation_path": "code/lunalink/exporters.py",
        "test_path": "code/tests/test_main_simulation.py",
        "validation_metric": "external correlation pending; scenario export complete",
        "evidence_artifact": "scenario_exports/LunaLink_external_validation_recipe.md",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LunaLink mission simulation.")
    parser.add_argument("--out", default="outputs/baseline", help="Output directory.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a faster coarse 36 h smoke-test run.",
    )
    parser.add_argument("--two-body", action="store_true", help="Disable J2 perturbation.")
    return parser.parse_args()


def build_config(quick: bool) -> MissionConfig:
    base = default_mission_config()
    if not quick:
        return base
    return MissionConfig(
        orbit=base.orbit,
        spacecraft=base.spacecraft,
        ground_station=base.ground_station,
        simulation=SimulationConfig(
            epoch_utc=base.simulation.epoch_utc,
            duration_s=36.0 * 3600.0,
            output_step_s=600.0,
        ),
    )


def main() -> int:
    os.environ.setdefault("MPLCONFIGDIR", ".cache/matplotlib")
    args = parse_args()
    output_dir = ensure_directory(Path(args.out))
    config = build_config(args.quick)
    results = run_mission(config, include_j2=not args.two_body)
    validation_df = metrics_to_dataframe(results.validation_metrics)
    trade_df = eps_pareto_grid([4.0, 5.0, 6.0, 7.0], [3.0, 4.5, 6.0], results.environment)
    uncertainty_bounds = {
        "array_area_m2": (4.0, 7.0),
        "battery_capacity_kwh": (3.0, 6.0),
        "solar_array_eta_eol": (0.24, 0.30),
        "xband_tx_power_w": (15.0, 30.0),
    }
    lhs_df = latin_hypercube_samples(uncertainty_bounds, n_samples=24, seed=42)
    mc_df = monte_carlo_samples(uncertainty_bounds, n_samples=24, seed=42)
    figures = save_basic_figures(results, output_dir, trade_df=trade_df)
    scenario_exports = write_scenario_exports(config, output_dir / "scenario_exports")

    write_json(
        output_dir / "run_manifest.json",
        {
            "tool": "LunaLink",
            "mode": "quick" if args.quick else "baseline",
            "include_j2": not args.two_body,
            "critical_failures": has_critical_failures(results.validation_metrics),
            "figures": figures,
            "scenario_exports": scenario_exports,
        },
    )
    write_json(output_dir / "assumptions.json", {"mission": asdict(results.config)})
    write_json(output_dir / "subsystem_summaries.json", results.summaries)
    write_dataframe(output_dir / "mission_timeseries.csv", results.environment)
    write_dataframe(output_dir / "eps_timeseries.csv", results.eps)
    write_dataframe(output_dir / "thermal_timeseries.csv", results.thermal)
    write_dataframe(output_dir / "adcs_timeseries.csv", results.adcs)
    write_dataframe(output_dir / "ttc_timeseries.csv", results.ttc)
    write_dataframe(output_dir / "trade_results.csv", trade_df)
    write_dataframe(output_dir / "lhs_samples.csv", lhs_df)
    write_dataframe(output_dir / "monte_carlo_samples.csv", mc_df)
    write_dataframe(output_dir / "validation_metrics.csv", validation_df)
    write_dataframe(output_dir / "formula_traceability.csv", pd.DataFrame(TRACEABILITY_ROWS))

    print(f"Wrote LunaLink evidence bundle to {output_dir}")
    print(validation_df[["name", "status", "value"]].to_string(index=False))
    return 1 if has_critical_failures(results.validation_metrics) else 0


if __name__ == "__main__":
    raise SystemExit(main())
