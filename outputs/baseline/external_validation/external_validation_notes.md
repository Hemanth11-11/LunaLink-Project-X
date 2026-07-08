# External Validation Notes

The baseline evidence bundle includes GMAT/Orekit-style scenario seeds:

- `outputs/baseline/scenario_exports/LunaLink_GMAT_scenario.script`
- `outputs/baseline/scenario_exports/LunaLink_Orekit_scenario.json`

These files support independent cross-checking. They are not proof that GMAT or
Orekit has been executed.

## Required Future Comparison

| Item | LunaLink source | External source | Status |
| --- | --- | --- | --- |
| Initial orbit elements | `assumptions.json` | GMAT/Orekit scenario | scenario seed exported |
| Orbit period | `validation_metrics.csv` | external propagation | pending |
| Altitude envelope | `mission_timeseries.csv` | external ephemeris | pending |
| Ground contacts | `ttc_timeseries.csv` | external access report | pending |
| Eclipse intervals | `mission_timeseries.csv` | external eclipse report | pending |

Formal validation requires independent execution, toleranced diffs, and review
sign-off.
