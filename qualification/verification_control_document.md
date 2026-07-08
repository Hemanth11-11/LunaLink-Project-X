# Verification Control Document

## Verification Commands

```bash
MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
.venv/bin/ruff check code
MPLCONFIGDIR=.cache/matplotlib .venv/bin/python code/main_simulation.py --quick --out outputs/ci
MPLCONFIGDIR=.cache/matplotlib .venv/bin/python report/build_report.py --evidence outputs/ci --out report/LunaLink_Report_Draft.md
```

## Verification Methods

| Method | Meaning |
| --- | --- |
| Test | Automated pytest unit or integration test. |
| Analysis | Deterministic calculation checked against a formula or criterion. |
| Inspection | Human review of generated evidence, figures, and documents. |
| Similarity | Planned comparison against external GMAT/Orekit truth-style tools. |

## Current Verification Status

| Area | Method | Current status |
| --- | --- | --- |
| Orbit period and duration | Test, analysis | Automated validation metrics |
| Ground contact geometry | Test, analysis | Automated validation metrics |
| EPS energy balance | Test, analysis | Automated unit tests and run evidence |
| TT&C link budget | Test, analysis | Automated unit tests and run evidence |
| TCS thermal trend | Test, analysis | Automated unit tests and run evidence |
| ADCS detumble | Test, analysis | Automated unit tests and run evidence |
| Report generation | Test | Automated builder test |
| GUI launch path | Test, inspection | Import/config test; headless Streamlit smoke launch completed |
| External correlation | Similarity | Scenario exports generated; formal comparison pending |

## Requirement Verification Matrix

| Requirement | Method | Success criterion | Tolerance | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-MIS-001 | Analysis, test | 500 x 36,000 km orbit period near 10.6845 h | +/- 0.01 h | `validation_metrics.csv` | pass |
| REQ-MIS-002 | Test | Duration at least 36 h | no underrun | `validation_metrics.csv` | pass |
| REQ-MIS-003 | Test | Contact samples at or above 5 deg elevation | no violating contact sample | `validation_metrics.csv`, `ttc_timeseries.csv` | pass |
| REQ-EPS-001 | Analysis, test | SOC above 20%, no unserved energy, 1.2 kW EOL closure | no critical fail | `eps_timeseries.csv`, `validation_metrics.csv` | pass |
| REQ-TCS-001 | Analysis, test | No internal/external component limit flags | no critical fail | `thermal_timeseries.csv`, `validation_metrics.csv` | pass |
| REQ-TCS-002 | Analysis, test | Worst preliminary thermal hot/cold margin at least 5 K | no warning | `thermal_timeseries.csv`, `validation_metrics.csv` | pass |
| REQ-ADCS-001 | Analysis, test | Final detumble rate below 0.05 deg/s, no wheel saturation | no critical fail | `adcs_timeseries.csv`, `validation_metrics.csv` | pass |
| REQ-TTC-001 | Analysis, test | X-band and UHF margins above 3 dB; X-band rate at least 100 Mbps | no critical fail | `ttc_timeseries.csv`, `validation_metrics.csv` | pass |
| REQ-TRADE-001 | Test | Reproducible Monte Carlo and Latin Hypercube samples | fixed seed repeatability | `lhs_samples.csv`, `monte_carlo_samples.csv` | pass |
| REQ-TRADE-002 | Inspection | Pareto-style EPS trade plot generated | file exists | `figures/pareto_eps_trade.png` | pass |
| REQ-EVID-001 | Demonstration | Evidence bundle generated from CLI | command exits 0 | `outputs/baseline/` | pass |
| REQ-EVID-002 | Demonstration | Markdown report generated from evidence | command exits 0 | `report/LunaLink_Baseline_Report.md` | pass |
| REQ-EVID-003 | Demonstration | Streamlit dashboard starts in headless mode | server binds to 127.0.0.1 | `qualification/dashboard_smoke_test.md` | pass |
| REQ-XCHK-001 | Inspection | GMAT/Orekit-style scenario seeds exported | files exist | `scenario_exports/` | pass for export; external run pending |

No flight-qualified claim is permitted until independent verification,
requirements closure, configuration management, and authority acceptance are
complete.
