# Model Validation Report

## Scope

This report records the validation status for the LunaLink preliminary
engineering simulator. It supports academic and early design use only.

## Evidence Baseline

- Evidence directory: `outputs/baseline`
- Report: `report/LunaLink_Baseline_Report.md`
- Validation table: `outputs/baseline/validation_metrics.csv`
- Test suite: `54 passed`
- Static check: `ruff check code` passed

## Subsystem Review Disposition

| Area | Expert finding | Disposition |
| --- | --- | --- |
| Orbit/frames | ECI/ECEF sign and WGS84 traceability needed improvement. | Fixed passive rotation sign, added WGS84 geodetic output and tests. |
| EPS | Array incidence and 1.2 kW EOL closure needed explicit validation. | Added sun-tracking/fixed-array incidence modes and EOL power/load validation. |
| TCS | Fixed view factors and scalar average power were too weak. | Added dynamic face view factors, mixed coatings, and time-varying EPS load. |
| ADCS | Full Euler dynamics and disturbance torque evidence were needed. | Added RK4 Euler-rate integration, SRP, drag, residual magnetic torque, and diagnostics. |
| TT&C | RF math was sound, but evidence columns and data-volume semantics were thin. | Added richer link budget columns and end-to-end/aggregate volume distinction. |

## Current Validation Result

All critical metrics pass in `outputs/baseline/validation_metrics.csv`.

## External Correlation Status

GMAT/Orekit-style scenario exports are generated, but independent external
execution and toleranced comparison are not complete. This remains a
certification-readiness task, not a blocker for the academic simulator.

## Validity Boundary

The simulator is valid for preliminary design trades and evidence-backed
assignment reporting. It is not valid for operations, flight safety decisions,
or certified mission analysis without independent correlation and authority
acceptance.
